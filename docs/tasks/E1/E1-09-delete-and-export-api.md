# E1-09 · "Delete my data" and export API

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | Data deletion SLO (added to `docs/metrics.md` by E1-03) |
| Depends on | E1-07c, E1-03 |
| ADRs | retention ADR (E1-03), 008 |
| Design spec | `docs/design/flows.md` (F10, "Guest data") |

## Why

As a guest or account holder, I want to delete everything Capsule holds about me with one action, so that I stay in control of my data (GDPR right to erasure). As a user, I want to download my data, so that I can see what is stored (right of access and portability).

## Acceptance criteria

- [ ] Contract first: delete and export operations for the current principal (e.g. `DELETE /v1/me`, `GET /v1/me/export`). Both work for guests and accounts.
- [ ] Delete removes every row owned by the principal and revokes all its tokens and credentials before it responds (the app wipes local data only after success, flows.md F10). Calling it again for a deleted principal returns 401, never 500.
- [ ] In the same transaction, delete writes the principal id to the deletion ledger through the E1-07c writer, and collects the principal's media object keys before the commit (ADR-022).
  - After commit and before responding, the writer appends the id to the external ledger file, and the media hook deletes the collected keys.
  - A failed append or a missing ledger disk keeps the deletion, returns success and logs an error with the principal id only.
  - A failed media delete is left to the ADR-008 job.
  - Tests: the ledger row, a failed append, and keys collected before commit.
- [ ] Every module that stores user data registers its delete and export handlers with the auth service, so E3+ tables join without changing this card's code. A test fails if a table holding user data has no handler (the check covers the tables that exist now).
- [ ] Export returns the format set by the retention ADR. It includes the account email for accounts and never includes password hashes or tokens.
- [ ] Media deletion follows ADR-008 when media exist (none in E1). The test proves the hook is called.
- [ ] No personal data in logs. A deletion is logged only as a count with the principal type.
- [ ] Tests:
  - [ ] Integration (real Postgres): guest delete, account delete, the old refresh token fails after delete, export contents.
  - [ ] Contract.
  - [ ] Failure path: a DB error midway leaves everything in place and returns a problem document.

## Allowed files

- `contracts/openapi.yaml`
- `apps/api/modules/auth/**`, `apps/api/core/**`, `apps/api/migrations/**`, `apps/api/main.py`
- `apps/api/tests/**`

## Out of scope

- PostHog and Sentry deletion. The app resets its ids; server-side deletion through those APIs is E2.
- Expiring guest data automatically (E1-10). Mobile UI (E1-14).

## Analytics events

- none. No event is sent for deletion; the analytics id is reset (flows.md).

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
- Numbers:
- Left for later:
