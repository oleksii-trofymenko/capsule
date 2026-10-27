# E1-30 · Least-privilege S3 identity for the api

| Field | Value |
| --- | --- |
| Status | todo (backlog: before the first card that gives `api` S3 access; that card lists E1-30 in Depends on) |
| Owner | security-engineer (ADR) → platform-engineer (SeaweedFS identities) with backend-engineer (api settings) |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | n/a — security control (least privilege for media storage); no product metric or SLO moves |
| Depends on | E1-25 |
| ADRs | 008, 015, 024; a new ADR (see criteria) |
| Design spec | none |

## Why

SeaweedFS has one S3 identity today: the admin identity created from `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. If `api` signs presigned URLs with that identity, a leaked api key, or a bug in URL signing, gives full control of every bucket. `api` should only read and write objects in the media bucket. SeaweedFS environment variables create only the admin identity, so a second identity needs an identities config file, which ADR-015 deferred (option 5).

## Acceptance criteria

- [ ] A new ADR, accepted by the owner before code starts, supersedes the parts of ADR-015 it changes: where S3 identities are stored (the identities file, its owner and mode, which services mount it) and the inventory row for the api identity. If the identities file changes or removes the SeaweedFS startup line ADR-024 covers, or a new line logs the api access key ID, the same ADR (or another one) supersedes ADR-024. Accepted ADRs are not edited.
- [ ] A second S3 identity limited to `Read` and `Write` (plus `List` only if needed) on the media bucket. `api` gets only that identity; the admin identity stays with `seaweedfs` and operator tools.
- [ ] Presigned URLs signed with the api identity work for upload and download; the same identity is refused for another bucket, bucket creation and bucket deletion. A test proves each one.
- [ ] Every new secret value is masked in CI and in the leak patterns.
- [ ] `check-seaweedfs.sh` still passes.
- [ ] Tests: the checks above on the stack; the CI `stack` job green.
- [ ] Docs: `docs/security.md` asset rows for the api identity; `docs/runbooks/secret-leak.md` and `docs/runbooks/key-rotation.md` rows for the new key.

## Allowed files

- `docs/adr/0xx-*.md` (the new ADR), `docs/adr/README.md` (new row, and the status of any ADR it supersedes)
- `infra/compose/**`, `.env.example`, `.github/workflows/ci.yml` (`stack` job)
- `apps/api/core/config.py`, `apps/api/tests/**`
- `docs/security.md` (S3 asset rows only), `docs/runbooks/secret-leak.md`, `docs/runbooks/key-rotation.md`, `docs/runbooks/compose-stack.md`

## Out of scope

- The media upload endpoints themselves (E2). Log redaction of presigned-URL signatures (E2-01).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the E1-05b security review; ADR route added after the PR #30 review.
- Numbers:
- Left for later:
