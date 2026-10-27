# E1-30 · Least-privilege S3 identity for the api

| Field | Value |
| --- | --- |
| Status | todo (backlog: before the first card that gives `api` S3 access) |
| Owner | platform-engineer (SeaweedFS identities) with backend-engineer (api settings) |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | n/a — security control (least privilege for media storage); no product metric or SLO moves |
| Depends on | E1-25 |
| ADRs | 008, 015, 024 |
| Design spec | none |

## Why

SeaweedFS has one S3 identity today: the admin identity created from `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. If `api` signs presigned URLs with that identity, a leaked api key, or a bug in URL signing, gives full control of every bucket. `api` should only read and write objects in the media bucket.

## Acceptance criteria

- [ ] A second S3 identity limited to `Read`, `Write` (and `List` only if needed) on the media bucket. `api` gets only that identity; the admin identity stays with `seaweedfs` and operator tools.
- [ ] Presigned URLs signed with the api identity work for upload and download; the same identity is refused for another bucket, bucket creation and bucket deletion. A test proves each one.
- [ ] The new secret key follows ADR-015 (file secret for `api` only, masked in CI, in the leak patterns). The access key ID follows ADR-024 if SeaweedFS logs it.
- [ ] If the identities move to a config file, recheck whether the ADR-024 startup line still appears. Withdraw ADR-024 if it does not.
- [ ] `check-seaweedfs.sh` still passes.
- [ ] Tests: the checks above on the stack; the CI `stack` job green.
- [ ] Docs: `docs/runbooks/secret-leak.md` and `docs/runbooks/key-rotation.md` rows for the new key.

## Allowed files

- `infra/compose/**`, `.env.example`, `.github/workflows/ci.yml` (`stack` job)
- `apps/api/core/config.py`, `apps/api/tests/**`
- `docs/runbooks/secret-leak.md`, `docs/runbooks/key-rotation.md`, `docs/runbooks/compose-stack.md`
- `docs/adr/024-s3-access-key-id-not-secret.md` and `docs/adr/README.md` (024 row only, to withdraw it)

## Out of scope

- The media upload endpoints themselves (E2). Log redaction of presigned-URL signatures (E2-01).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the E1-05b security review.
- Numbers:
- Left for later:
