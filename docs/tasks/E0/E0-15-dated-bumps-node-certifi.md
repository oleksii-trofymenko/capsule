# E0-15 · Dated bumps: Node 24.22.1 and the certifi audit ignore

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | n/a — dependency hygiene (ADR-018/019 7-day rule) |
| Depends on | none |
| ADRs | 016, 018, 019 |
| Design spec | none |

## Why

Two dated items are now eligible under the 7-day rule: Node 24.22.1 (CI pins 24.22.0), and the `exclude-newer` bump that removes the temporary `PYSEC-2026-4320` ignore for certifi (review deadline 2026-11-09).

## Acceptance criteria

- [ ] `NODE_VERSION` in `.github/workflows/ci.yml` is `24.22.1`, and any other Node pin that `check-pins.sh` compares moves with it.
- [ ] `exclude-newer` in `apps/api/pyproject.toml` moves to a date ≥ 2026-10-27 that is still at least 7 days old; `uv.lock` is regenerated; certifi resolves to 2026.10.19 or later.
- [ ] The `--ignore-vuln PYSEC-2026-4320` line and its comment are removed from `ci.yml`; the audit job passes without it.
- [ ] Any other package the lock moves is listed in the PR with its version change, and none is newer than 7 days.
- [ ] Tests: `make lint`, `make test` and CI green.

## Allowed files

- `.github/workflows/ci.yml`, `apps/api/pyproject.toml`, `apps/api/uv.lock`, `infra/compose/check-pins.sh` (only if it pins Node)

## Out of scope

- Redis 8.10.3 (eligible 2026-11-02, separate card). SeaweedFS bump (waits for the upstream release with PR #12085).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the E0-13/E0-14 hand-off.
- Numbers:
- Left for later:
