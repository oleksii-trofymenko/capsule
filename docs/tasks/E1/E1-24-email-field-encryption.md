# E1-24 · Encryption at rest: account email with a blind index (before external beta)

| Field | Value |
| --- | --- |
| Status | todo (backlog: before external beta; not part of the E1 demo) |
| Owner | security-engineer (scheme, in the plan step) → backend-engineer (implementation) |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | n/a — security control for threat D4; no product metric or SLO moves (sign-up and sign-in latency stay inside "API latency (simple endpoints)", checked in the PR) |
| Depends on | E1-04, E1-07 |
| ADRs | 015 (keys), 007; a new ADR if the crypto library is not named in blueprint §4 or an accepted ADR |
| Design spec | none |

## Why

As an account holder, I want my email to stay unreadable if the server's disk or a database backup is stolen. Threat D4 in `docs/security.md` asks for encryption at rest before external users arrive. E1-25 covers the disk and media-key part of D4.

## Acceptance criteria

- [ ] The account email is stored only encrypted (authenticated encryption, with the key from ADR-015), plus a blind index, a keyed HMAC of the normalised email, for the uniqueness check and sign-in lookup. No plain email column remains.
- [ ] A migration moves existing rows and is safe to run twice. Its downgrade path is documented.
- [ ] Key rotation is possible. A key id is stored with each value, and the runbook describes rotating the key.
- [ ] Sign-up, sign-in, export (E1-09) and password reset (E1-17, if merged) keep working through the service interface. Export returns the decrypted email to its owner only.
- [ ] Backups (E1-23) contain only ciphertext for email. A test inspects a dump made in the test run.
- [ ] Tests: unit (encrypt/decrypt, blind index stable under normalisation, wrong key fails); integration with real Postgres (uniqueness through the blind index, sign-in lookup, migration of existing rows); latency of sign-in before and after recorded in Numbers.
- [ ] ADR-015: two separate 32-byte keys in `secrets/` (`email_encryption_keys` as `kid=hex` lines, the first encrypts; `email_blind_index_key`); before the first real email is stored, the owner confirms in Decisions that off-host copies exist (date only, no key material).

## Allowed files

- `apps/api/modules/auth/**`, `apps/api/core/**`, `apps/api/migrations/**`, `apps/api/pyproject.toml`, `apps/api/uv.lock`, `apps/api/tests/**`, `infra/compose/env-init.sh`, `docs/runbooks/key-rotation.md` (new), `docs/adr/0xx-*.md` and `docs/adr/README.md` (only if a library needs an ADR)
- ADR-015: `infra/compose/compose.base.yml` (`email_encryption_keys` and `email_blind_index_key` secret entries only); `docs/runbooks/secret-leak.md` (email-keys row); `docs/runbooks/key-rotation.md` (email section; E1-05 creates the file)

## Out of scope

- Host disk encryption and SeaweedFS keys (E1-25). Encrypting consultation data (decide in E3 with the threat model).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27: amended from E1-01 threat model (docs/security.md), threat D4. Split from the requested single card because field encryption and host/media keys together are over M; the second half is E1-25.
- Numbers:
- Left for later:
