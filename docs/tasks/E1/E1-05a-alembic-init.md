# E1-05a · Alembic init, migration runner and quiet Postgres errors

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | n/a — database plumbing; it unblocks E1-05 and every later table |
| Depends on | E0-06, E0-07 |
| ADRs | 007, 016, 022 |
| Design spec | none |

## Why

E1-05 is the first card that needs tables. Split out of E1-05 (2026-10-27) so the first migration setup, the way `make up` applies migrations and the Postgres logging rule from ADR-022 land in a small PR before the auth code.

## Acceptance criteria

- [ ] `alembic` is a runtime dependency of `apps/api` (named in ADR-007; release at least 7 days old, under the `exclude-newer` cutoff).
- [ ] `apps/api/alembic.ini` and `apps/api/migrations/` with `env.py` reading the database URL from `core/config.py`, and an empty baseline revision.
- [ ] Migrations run on `make up` before `api` takes traffic (for example a one-shot `migrate` service that `api` depends on with `service_completed_successfully`). `make up` still waits for `/v1/ready`.
- [ ] The API image contains `migrations/` and `alembic.ini` (`apps/api/.dockerignore` allows them).
- [ ] ADR-022 (logs): Postgres runs with `log_error_verbosity=terse` and `log_min_error_statement=panic`, set in the `postgres` service `command` in `infra/compose/compose.base.yml`. Error lines then carry no DETAIL, CONTEXT or STATEMENT with row values. The CI `stack` job asserts both settings with `SHOW` against the real stack (GitHub service containers cannot take a `command`, so the integration job cannot).
- [ ] Tests: a fixture upgrades the test database to head; a test runs upgrade → downgrade → upgrade; `make test` and CI (including the `stack` job) green.
- [ ] Docs: `apps/api/CLAUDE.md` says how to add a migration; root `CLAUDE.md` Commands updated only if a Make target is added.

## Allowed files

- `apps/api/pyproject.toml`, `apps/api/uv.lock`, `apps/api/alembic.ini`, `apps/api/migrations/**`, `apps/api/core/**` (database URL only), `apps/api/.dockerignore`, `apps/api/Dockerfile` (only if the migrate step needs it), `apps/api/tests/**`, `apps/api/CLAUDE.md`
- `infra/compose/compose.base.yml` (`postgres` service `command` and the migrate step only), `Makefile` (`up` target: a `run --rm migrate` step only if Compose `--wait` rejects an exited one-shot) and root `CLAUDE.md` Commands (only if a target is added), `.github/workflows/ci.yml` (`stack` job: the `SHOW` step only), `docs/runbooks/compose-stack.md` (migration section)

## Out of scope

- Any application table (E1-05). JWT keys (E1-05b).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - 2026-10-27 (plan): one-shot `migrate` service with the api image and hardening, `api` waits for `service_completed_successfully`; sync Alembic env (psycopg 3 sync); `alembic>=1.20.0,<1.21`; the `SHOW` check runs in the CI `stack` job.
  - Filed 2026-10-27, split out of E1-05 (backend-engineer plan: E1-05 with ADR-015 and ADR-022 additions came to ~1,300–1,500 lines).
- Numbers:
- Left for later:
  - `terse` does not hide role names in Postgres auth-failure lines; consider a card.
