# E1-31 · Enforce module boundaries with Ruff banned imports

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer |
| Estimate | S |
| Metric | n/a — harness card (lint rule); no product metric or SLO moves |
| Depends on | E1-05 |
| ADRs | 005 |
| Design spec | none |

## Why

ADR-005 and `apps/api/CLAUDE.md` say module boundaries are enforced by Ruff banned-import rules, but the root `pyproject.toml` only bans relative imports. Once `modules/auth` exists (E1-05), other modules could import its internals (repository, tokens) instead of its public interface, and nothing would stop them.

## Acceptance criteria

- [ ] Each module's internal submodules (for `modules.auth`: repository, tokens, service, router, schemas, dependencies) are listed in Ruff `banned-api`, with `per-file-ignores` for the module itself and its tests. Other code imports only `modules.<name>` (its `__init__` interface). No new dependency.
- [ ] `apps/api/CLAUDE.md` says a new module adds its `banned-api` and `per-file-ignores` entries.
- [ ] Log calls cannot pre-format their message: Ruff `G001`–`G004` (f-string, `%`, `.format`, `+` in a logging call) and `PLE1205`/`PLE1206` (argument-count mismatch) are on. E1-05d's formatter cleans exception objects only; text formatted before the logger sees it is not caught (E1-05d security review, L3). Objects that embed an exception in their own `repr` remain a documented limit in `core/logging.py`.
- [ ] `migrations` is added to `known-first-party` (E1-05a left for later).
- [ ] Proof: a scratch file that imports `modules.auth.repository` from `core/` fails `make lint`; the result is in Numbers and the file is not committed.
- [ ] Tests: `make lint` and `make test` green on the current code.

## Allowed files

- `pyproject.toml` (Ruff settings only), `apps/api/CLAUDE.md` (the module-boundary line only), and `apps/api/**` import lines only if current code breaks the new rule

## Out of scope

- Import rules for `apps/mobile`.

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - 2026-10-27: added the logging lint rules (E1-05d security review, L3).
  - Filed 2026-10-27 from the backend-engineer E1-05 plan (risk 5) and the E1-05a "Left for later" Ruff note.
- Numbers:
- Left for later:
