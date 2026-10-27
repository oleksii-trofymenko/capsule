# E2-02 · Secret key-age panel and alert

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | n/a — operations control for ADR-015 key rotation; no product metric or SLO moves |
| Depends on | E1-05; the first E2 Grafana card (ID to add once it is filed) |
| ADRs | 015 |
| Design spec | none |

## Why

ADR-015 ("We will monitor") rotates the JWT signing keys by hand every 90 days. Nothing reminds the owner today; `docs/runbooks/key-rotation.md` says to note the date by hand (E1-05b, left for later).

## Acceptance criteria

- [ ] `api`, which already reads `/run/secrets/jwt_signing_keys` at start (ADR-015: no other service gets the file), exposes the age in days of the newest key as a metric, computed from the `YYYY-MM-DD` `kid`. No key value goes into any metric, log or label.
- [ ] A Grafana panel shows that metric.
- [ ] An alert fires when the newest key is older than 100 days.
- [ ] Proof: a test file with an old `kid` makes the alert fire; the metric output holds no hex longer than the date.
- [ ] Tests: the proof above; the CI `stack` job green.
- [ ] Docs: `docs/runbooks/key-rotation.md` points to the panel instead of the by-hand note.

## Allowed files

- `apps/api/core/**` (key-age metric), `apps/api/tests/**`, `infra/**` (dashboard, alert rule), `docs/runbooks/key-rotation.md`

## Out of scope

- Automatic rotation. Other secrets (add rows when their rotation is scheduled).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from E1-05b "Left for later" (PR #30 review).
- Numbers:
- Left for later:
