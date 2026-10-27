# E1-26 · Separate Postgres roles for api and migrate

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | platform-engineer (Compose, env-init, CI) with backend-engineer (migration grants) |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | n/a — security control (least privilege for the database); no product metric or SLO moves |
| Depends on | E1-05 |
| ADRs | 015, 022 |
| Design spec | none |

## Why

Today `api` and `migrate` both connect as `POSTGRES_USER`, the superuser the image creates. A SQL injection or a compromised `api` process could then drop tables, read every schema or run `COPY ... TO PROGRAM`. Only `migrate` needs to change the schema (E1-05a review, out of scope there).

## Acceptance criteria

- [ ] Three roles: the bootstrap superuser (used only by the Postgres image and by `migrate`'s first-run grant, or not at all after init), a schema-owner role for `migrate`, and a `NOSUPERUSER NOCREATEDB NOCREATEROLE` role for `api` with only `SELECT, INSERT, UPDATE, DELETE` on the app tables and `USAGE` on their sequences.
- [ ] Grants come from a migration (or `ALTER DEFAULT PRIVILEGES` run by the owner role), so a table added later is reachable by `api` without a manual step.
- [ ] `env-init.sh` generates the new passwords with the same hex-length checks as the existing values. An existing `.env` without them gets them added on the next `make up`, and an existing `pg_data` volume is migrated (or the runbook gives the one-time step).
- [ ] `api` cannot `CREATE TABLE`, `DROP TABLE`, `TRUNCATE` or `COPY ... PROGRAM`. A test on the stack proves each one is refused.
- [ ] The CI leak check covers the new passwords (they join the patterns like every `.env` value).
- [ ] Decide, and record in Decisions, whether role names in Postgres auth-failure log lines need hiding (`terse` keeps them; E1-05a left for later). Role names are not secrets; a change needs a reason.
- [ ] Tests: integration test as the `api` role; `make up` on a fresh and an existing volume; the CI `stack` job green.
- [ ] Docs: `docs/runbooks/compose-stack.md` (roles and the upgrade step), `infra/compose/README.md`.

## Allowed files

- `infra/compose/**`, `.env.example`, `.github/workflows/ci.yml` (`stack` job)
- `apps/api/migrations/**`, `apps/api/tests/**`, `apps/api/core/config.py` (only if the api URL variable changes)
- `docs/runbooks/compose-stack.md`

## Out of scope

- Row-level security. Separate roles for the worker (until the worker touches Postgres). Backups (E1-23).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the E1-05a review (security-engineer).
- Numbers:
- Left for later:
