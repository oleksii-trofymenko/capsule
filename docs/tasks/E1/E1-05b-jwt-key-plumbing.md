# E1-05b · JWT signing-key plumbing (ADR-015)

| Field | Value |
| --- | --- |
| Status | review |
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
  - [ ] Git Bash: `MSYS2_ARG_CONV_EXCL='*'`; `icacls` grants the user SID (from `whoami /user`) and SYSTEM with (OI)(CI) on `secrets/`, inheritance removed, Administrators removed; `.env` gets plain `F` for the same two, inheritance and Administrators removed. The SID comes from `whoami.exe /user` via `cygpath` (Git Bash's own `whoami` cannot).
  - [ ] Linux: `secrets/` 0700; the key file `root:10001` 0440 via sudo; a clear error when sudo is missing.
- [ ] The file is mounted as a Compose file secret into `api` only (top-level `secrets:` block and the `api` `secrets:` list). No other service gets it.
- [ ] CI `stack` job: generate (`env-init.sh . generate-only`), then mask each key value separately, then apply the layout (after it, the runner reads the files only with `sudo`); fail if any generated value appears in the stack logs. `.env` and `secrets/` are never uploaded. A step proves `api` can read the file: `exec -T api test -r /run/secrets/jwt_signing_keys`.
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

- Plan approved: 2026-10-27 (Orchestrator). PR #28 (draft).
- Decisions:
  - 2026-10-27 (plan): `generate-only` argument makes generate → mask → layout literal; Linux layout skipped when `stat` already shows `0:10001 440` (no sudo prompt every `make up`); a missing file path that Docker turned into a folder fails loudly; leak check runs before `make down` and after the restart.
  - 2026-10-27 (build): paths go to `icacls` through `cygpath -w`. `MSYS2_ARG_CONV_EXCL='*'` turns off conversion for every argument, so a POSIX root such as `/tmp/...` would otherwise reach icacls unconverted.
  - 2026-10-27 (build): CI masking fails on any file in `secrets/` without a masking rule, so E1-08, E1-17 and E1-24 cannot add a secret and skip masking. Logs go into a variable for the leak check, not a pipe: with pipefail, `grep -q` closing the pipe early would hide a hit.
  - 2026-10-27 (build): the consumer GID is one constant in `env-init.sh` (`API_GID=10001`, from `apps/api/Dockerfile`).
  - 2026-10-27 (build): container paths in Git Bash need `MSYS_NO_PATHCONV=1` (`/run/secrets/...` is otherwise rewritten to `C:/Program Files/Git/run/...`). Found during local verification; the runbook check carries it.
  - 2026-10-27 (build): local `make up` timings used an isolated project (`capsule-e105b`, port 18005), because E1-05a shared the same Docker Desktop on project `capsule`. The owner's own checkout gets its `secrets/` on the first `make up` after merge.
- Numbers:
  - `make up` from a fresh `.env` (images and build cache warm, Git Bash, Docker Desktop 29.8.2): before 7 s (main `1799a6d`), after 7 s. A second run with existing files: 2 s, key file and `.env` unchanged (sha256).
  - CI `stack` job: before 69 s (run 40534412700, main), after 73 s (run 40536049099, PR #28). Whole run 1 m 31 s → 1 m 32 s. All checks green, `ci-ok` pass.
  - CI evidence: `secrets/jwt_signing_keys: 1 value(s) masked`; `secrets runner:1001 700`, `secrets/jwt_signing_keys root:10001 440`; the runner cannot read it, `sudo test -r` can; `api reads its file secret` pass; `none of the 1 generated value(s) appear in the logs` after the restart (and the check before `make down` passed).
  - Lint job `compose config --quiet` with no `secrets/`: pass on ubuntu-24.04 image 20261012.334.1, Docker Compose 2.38.2 (and locally on Compose v5.5.1).
  - Local Git Bash: `icacls` on `secrets/`, the key file and `.env` shows only SYSTEM and the user; a uid 10001 `--read-only` container reads the file; in the stack only `api` has `/run/secrets/jwt_signing_keys`; the Linux branch was checked in a container (root, non-root without sudo, already correct).
  - "Secrets in repository" stays 0 (`make lint`, gitleaks history).
- Left for later:
  - Key-age panel with an alert above 100 days (ADR-015 "We will monitor"): E2, when Grafana exists. Until then `key-rotation.md` says to note the date by hand.
  - ADR-015 asks CI to grep every masked value, including the `.env` values. This card greps only the `secrets/` values (its scope). Extend the pattern file when E1-08 moves the SeaweedFS keys to `secrets/`, or with a small card.
