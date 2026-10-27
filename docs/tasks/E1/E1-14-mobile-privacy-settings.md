# E1-14 · Mobile: Settings → Privacy (S1), Delete my data and Download my data

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | mobile-engineer |
| Reviewers | code-reviewer, security-engineer, product-designer |
| Estimate | M |
| Metric | Data deletion SLO (added to `docs/metrics.md` by E1-03) |
| Depends on | E1-09, E1-11, E1-12, E1-20 |
| ADRs | 003, retention ADR (E1-03) |
| Design spec | S1 from E1-11; `docs/design/flows.md` F10 |

## Why

As a guest or account holder, I want to delete all my data, or download it, from Settings, so that I am in control of what Capsule keeps about me.

## Acceptance criteria

- [ ] S1 is built to the E1-11 spec.
- [ ] Delete follows flows.md F10 exactly:
  - [ ] Confirm dialog with `privacy.delete.body_guest` or `privacy.delete.body_account`.
  - [ ] The server deletion runs first. Only after success are secure-store and MMKV wiped (including saved guides), and then `privacy.delete.done` is shown.
  - [ ] On failure nothing local is wiped, and `error.server.title` + `error.try_again` is shown.
  - [ ] Offline: `privacy.delete.offline`, button disabled.
- [ ] After deletion, the app starts as a new guest.
- [ ] Download my data saves or shares the export file through the OS share sheet. Offline: disabled, with a reason.
- [ ] The two consent switches are not built here. They arrive with the SDKs (E2/E3), in the place the S1 spec reserves for them.
- [ ] Tests: Jest + RNTL for success, failure (nothing wiped), offline, guest vs account copy. A Maestro step in `e2e/auth.yaml` or its own flow: sign up → delete → the app is a guest again.

## Allowed files

- `apps/mobile/app/**`, `apps/mobile/features/profile/**`, `apps/mobile/shared/**`, `apps/mobile/package.json`, `apps/mobile/package-lock.json` (only for a share or file module named by an accepted ADR or blueprint §4)
- `apps/mobile/e2e/**`, `apps/mobile/**/__tests__/**`

## Out of scope

- Server-side PostHog and Sentry deletion (E2). Consent SDK wiring (E2/E3).

## Analytics events

- none. No event is sent for deletion or export (flows.md: deletion resets the analytics id).

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
- Numbers:
- Left for later:
