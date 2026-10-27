# E1-05b · JWT signing-key plumbing (ADR-015)

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S–M |
| Metric | n/a — secrets handling; `docs/metrics.md` "Secrets in repository = 0" stays at 0 |
| Depends on | E1-04 |
| ADRs | 015, 014, 019 |
| Design spec | none |

## Why

E1-05 signs access tokens with keys that must never sit in env, logs or CI artefacts. Split out of E1-05 (2026-10-27): this card is the infra half — generating the key file, its per-OS layout, mounting it into `api` only and the CI checks — so E1-05 can stay backend-only.

## Acceptance criteria

- [ ] ADR-015: `env-init.sh` creates `secrets/jwt_signing_keys` (`kid=hex`, 32 random bytes, `kid` = UTC date) if missing and never overwrites it.
- [ ] On every `make up` it applies the layout and fails `make up` on any non-zero exit:
  - [ ] Git Bash: `MSYS2_ARG_CONV_EXCL='*'`; `icacls` grants the user SID (from `whoami /user`) and SYSTEM with (OI)(CI) on `secrets/`, inheritance removed, Administrators removed; `.env` gets plain `F` for the same two.
  - [ ] Linux: `secrets/` 0700; the key file `root:10001` 0440 via sudo; a clear error when sudo is missing.
- [ ] The file is mounted as a Compose file secret into `api` only (top-level `secrets:` block and the `api` `secrets:` list). No other service gets it.
- [ ] CI `stack` job: generate, then mask each key value separately, then apply the layout (after it, the runner reads the files only with `sudo`); fail if any generated value appears in the stack logs. `.env` and `secrets/` are never uploaded.
- [ ] `docker compose config --quiet` passes in the lint job with no `secrets/` files present (confirm on the runner's Compose version).
- [ ] `docs/runbooks/secret-leak.md` (new, JWT row and the general steps from ADR-015) and `docs/runbooks/key-rotation.md` (new, JWT section: 90-day manual rotation, 15-minute wait, restore uses the leak procedure).
- [ ] Tests: `make lint`, `make test`, CI green; a CI run shows the masked values never appear; locally on Git Bash, `icacls secrets` output in the PR shows only the user and SYSTEM.

## Allowed files

- `infra/compose/env-init.sh`, `infra/compose/compose.base.yml` (top-level `secrets:` block and the `api` `secrets:` list only), `infra/compose/test.env` (only if needed)
- `.env.example` (comment pointing to `secrets/` only)
- `.github/workflows/ci.yml` (`stack` job: sudo layout step, per-value masking of `secrets/`, leaked-value log check only)
- `docs/runbooks/secret-leak.md` (new), `docs/runbooks/key-rotation.md` (new; JWT section), `docs/runbooks/compose-stack.md` (secrets section)

## Out of scope

- Reading the key in the API and refusing to start with zero or more than two keys (E1-05). Other secrets (E1-08, E1-17, E1-24, E1-25).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27, split out of E1-05 (infra half of the ADR-015 criterion).
- Numbers:
- Left for later:
