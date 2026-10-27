# E1-05a · Alembic init, migration runner and quiet Postgres errors

| Field | Value |
| --- | --- |
| Status | review |
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

- [x] `alembic` is a runtime dependency of `apps/api` (named in ADR-007; release at least 7 days old, under the `exclude-newer` cutoff).
- [x] `apps/api/alembic.ini` and `apps/api/migrations/` with `env.py` reading the database URL from `core/config.py`, and an empty baseline revision.
- [x] Migrations run on `make up` before `api` takes traffic (for example a one-shot `migrate` service that `api` depends on with `service_completed_successfully`). `make up` still waits for `/v1/ready`.
- [x] The API image contains `migrations/` and `alembic.ini` (`apps/api/.dockerignore` allows them).
- [x] ADR-022 (logs): Postgres runs with `log_error_verbosity=terse` and `log_min_error_statement=panic`, set in the `postgres` service `command` in `infra/compose/compose.base.yml`. Error lines then carry no DETAIL, CONTEXT or STATEMENT with row values. The CI `stack` job asserts both settings with `SHOW` against the real stack (GitHub service containers cannot take a `command`, so the integration job cannot).
- [x] Tests: a fixture upgrades the test database to head; a test runs upgrade → downgrade → upgrade; `make test` and CI (including the `stack` job) green.
- [x] Docs: `apps/api/CLAUDE.md` says how to add a migration; root `CLAUDE.md` Commands updated only if a Make target is added.

## Allowed files

- `apps/api/pyproject.toml`, `apps/api/uv.lock`, `apps/api/alembic.ini`, `apps/api/migrations/**`, `apps/api/core/**` (database URL only), `apps/api/.dockerignore`, `apps/api/Dockerfile` (only if the migrate step needs it), `apps/api/tests/**`, `apps/api/CLAUDE.md`
- `infra/compose/compose.base.yml` (`postgres` service `command` and the migrate step only), `Makefile` (`up` target: a `run --rm migrate` step only if Compose `--wait` rejects an exited one-shot) and root `CLAUDE.md` Commands (only if a target is added), `.github/workflows/ci.yml` (`stack` job: the `SHOW` step only), `docs/runbooks/compose-stack.md` (migration section and the CI `SHOW` triage bullet), `infra/compose/README.md` (`migrate` rows in the service and privilege tables; added 2026-10-27, Orchestrator-approved after review)

## Out of scope

- Any application table (E1-05). JWT keys (E1-05b).

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-27 (PR #29)
- Decisions:
  - 2026-10-27 (implementation):
    - alembic 1.20.0 brings in Mako 1.4.3 and MarkupSafe 3.0.4; all three are older than the `exclude-newer` cutoff.
    - `database_url_from_env()` in `core/config.py` gives Alembic only `DATABASE_URL`, with no other settings required.
    - `env.py` is online-only (offline `--sql` is refused). It uses `NullPool` and `hide_parameters=True`, has no `fileConfig`, and leaves `target_metadata = None` until models exist. Migration files are named with a date first (`file_template`).
  - 2026-10-27: `migrate` has its health check disabled. Otherwise it inherits the image's `/v1/health` probe, which a one-shot never passes. `up --wait` accepts the exited-0 one-shot both locally (Compose v5.5.1) and on the CI runner, so the Makefile is unchanged.
  - 2026-10-27: verified on the stack that a unique violation logs only the `ERROR:` line, with no DETAIL or STATEMENT. The client still receives DETAIL, so application code must not log driver error details.
  - 2026-10-27 (review, code-reviewer and security-engineer approved; fixes in 0798a36 and 2ff10c3):
    - S1: a host that `urlsplit` cannot parse (`[secrethost]`) used to be quoted in the `ConfigError`. It now raises a fixed message `from None`.
    - S2: `prepend_sys_path = %(here)s`, so Alembic works from any directory.
    - M1 (migrate half): a failed run exits with only `migration failed: <type> (<driver type>); sqlstate=…; constraint=…` and no chained exception. `migrations/` became a package (`migrations/errors.py`), so that `env.py` and the tests share the sanitiser without mypy seeing the file twice. A connection failure shows no SQLSTATE; its reason is in the Postgres log. The API half goes to E1-05.
    - L2/S3: runbook covers the upgrade outage and INVALID-index cleanup after `CREATE INDEX CONCURRENTLY`. S6: Compose comment against merging `migrate` into `api`.
    - Out of scope, Orchestrator to file: S4 (`lock_timeout`) and separate DB roles.
  - 2026-10-27 (plan): one-shot `migrate` service with the api image and hardening, `api` waits for `service_completed_successfully`; sync Alembic env (psycopg 3 sync); `alembic>=1.20.0,<1.21`; the `SHOW` check runs in the CI `stack` job.
  - Filed 2026-10-27, split out of E1-05 (backend-engineer plan: E1-05 with ADR-015 and ADR-022 additions came to ~1,300–1,500 lines).
- Numbers (local: Windows, Docker Desktop, build cache warm; CI: ubuntu-24.04):
  - `make up` cold (new volumes, no api image): 13 s before → 16 s after.
  - `make up` warm (after `make down`): 20 s / 20 s before → 15 s / 20 s after. SeaweedFS registration dominates.
  - Migrate container (start → exit 0): 0.69 s cold, 0.62 s warm.
  - CI `stack` job: 69–80 s before (main runs) → 68 s after (run 40536723184). Its `make up` step: 4 s → 5 s.
  - `make test`: 69 passed (was 59), 74 after the review fixes.
  - After the review fixes: clean `make up` 11 s; CI `stack` 69 s (run 40539486212).
- Left for later:
  - `REDIS_URL` has the same leak S1 fixed for the database: `Settings.from_env` quotes a bracketed host (`'secrethost' does not appear to be an IPv4 or IPv6 address`). Not fixed here because `core/` was allowed for the database URL only; needs a card.
  - `tests/unit/test_migrations.py`: Ruff sorts `migrations` as third-party there, because the root `known-first-party` list does not name it. Cosmetic; add it the next time the root `pyproject.toml` changes.
  - `migrate` logs nothing on success (no Alembic logging). If operators want the applied revisions in logs, route Alembic through `core/logging`.
  - Not exercised locally: a failing `migrate` keeping `api` down. This relies on Compose's `service_completed_successfully`.
  - `terse` does not hide role names in Postgres auth-failure lines; consider a card.
