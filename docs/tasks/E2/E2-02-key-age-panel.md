# E2-02 · Secret key-age panel and alert

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | n/a — operations control for ADR-015 key rotation; no product metric or SLO moves |
| Depends on | the first E2 card that brings up Grafana |
| ADRs | 015 |
| Design spec | none |

## Why

ADR-015 ("We will monitor") rotates the JWT signing keys by hand every 90 days. Nothing reminds the owner today; `docs/runbooks/key-rotation.md` says to note the date by hand (E1-05b, left for later).

## Acceptance criteria

- [ ] A Grafana panel shows the age in days of the newest JWT signing key, read from the `YYYY-MM-DD` `kid` of each line in `secrets/jwt_signing_keys`. Only the `kid` dates leave the file; no key value is read into any metric, log or label.
- [ ] An alert fires when the newest key is older than 100 days.
- [ ] Proof: a test file with an old `kid` makes the alert fire; the metric output holds no hex longer than the date.
- [ ] Tests: the proof above; the CI `stack` job green.
- [ ] Docs: `docs/runbooks/key-rotation.md` points to the panel instead of the by-hand note.

## Allowed files

- `infra/**` (exporter or script, dashboard, alert rule), `docs/runbooks/key-rotation.md`

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
