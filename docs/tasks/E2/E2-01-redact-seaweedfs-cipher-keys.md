# E2-01 · Redact SeaweedFS cipher keys, auth headers and presigned-URL signatures before logs leave the host

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | n/a — privacy guard for the log pipeline (ADR-008 deletion promise) |
| Depends on | the E2 log-shipping card (Loki/Grafana) |
| ADRs | 008, 013 (planned) |
| Design spec | none |

## Why

SeaweedFS 4.48 logs the chunk `CipherKey` in plain text at error level (`reader_at.go:270`) when a read fails. Once logs ship to Loki, anyone with Grafana/Loki access could decrypt media that is still on a volume before vacuum — after the promised 24 h deletion (security-engineer, E0-12 review, rated medium). `-v` does not suppress it.

## Acceptance criteria

- [ ] The log collector pipeline for the seaweedfs container redacts the key before shipping (e.g. a `replace` stage on `(?i)cipher_?key\W*[^\s,}]+` → `CipherKey:[REDACTED]`).
- [ ] A test feeds the real SeaweedFS 4.48 log line through the pipeline and asserts no key leaves it.
- [ ] The same pipeline redacts, for every container, `Authorization` header values (`Bearer …`, `AWS4-HMAC-SHA256 …`) and presigned-URL query parameters `X-Amz-Signature` and `X-Amz-Credential`. A test feeds one sample line of each through the pipeline.
- [ ] Ship only warning level and above from seaweedfs unless a card justifies more.
- [ ] The CI `stack` job's "Dump stack logs" step filters seaweedfs `CipherKey` values the same way (public Actions logs), until the upstream fix lands.
- [ ] This card is an acceptance criterion of (or merged into) the first E2 card that ships container logs; logs must not be shipped without it.

## Allowed files

- `infra/**` (collector config), `docs/runbooks/**`, `.github/workflows/ci.yml` (`stack` log dump only)

## Out of scope

- Upstream fix and image bump (tracked separately; owner to decide on a private upstream report).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-26 from the E0-12 reviews.
  - 2026-10-27: added Authorization header and presigned-URL signature redaction (E1-05b security review; ADR-024 treats only the access key ID as an identifier).
  - 2026-10-27: added the CI log-dump criterion. Since E0-14 the `stack` job does an S3 read right after restart; on a regression it hits the failed-read path and the dump prints the key in a public log (security-engineer, E0-14 review, low: throwaway object only).
- Numbers:
- Left for later:
