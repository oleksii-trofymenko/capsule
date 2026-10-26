# E2-01 · Redact SeaweedFS cipher keys before logs leave the host

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
- [ ] Ship only warning level and above from seaweedfs unless a card justifies more.
- [ ] This card is an acceptance criterion of (or merged into) the first E2 card that ships container logs; logs must not be shipped without it.

## Allowed files

- `infra/**` (collector config), `docs/runbooks/**`

## Out of scope

- Upstream fix and image bump (tracked separately; owner to decide on a private upstream report).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-26 from the E0-12 reviews.
- Numbers:
- Left for later:
