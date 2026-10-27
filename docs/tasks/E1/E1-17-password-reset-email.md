# E1-17 · Password reset by email (before external beta)

| Field | Value |
| --- | --- |
| Status | todo (backlog: before external beta; not part of the E1 demo) |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | D7 retention (users back after 7 days; a forgotten password must not end the relationship) |
| Depends on | E1-07 |
| ADRs | new ADR for the email provider (not named in blueprint §4); 014, 015 |
| Design spec | to be added by product-designer before the mobile follow-up card |

## Why

As an account holder who forgot my password, I want to reset it from my email, so that I don't lose my saved guides. E1 ships with no email sending (owner decision, 2026-10-27), so until this card lands, a forgotten password means a lost account. That is acceptable for the demo but not for external users.

## Acceptance criteria

- [ ] A new ADR picks a transactional email service with a free tier that covers beta volume (€0 budget, EU data processing or adequate safeguards, DPA available). It also covers what happens when the free quota runs out.
- [ ] Contract first: request-reset and confirm-reset operations. Requesting a reset always returns the same response whether or not the email exists.
- [ ] The reset token is single-use, short-lived and stored only as a hash. A successful reset revokes every refresh family of the account.
- [ ] Rate limits per IP and per email on reset requests (reusing E1-08).
- [ ] The provider API key is stored as ADR-015 requires. Email bodies and addresses never appear in logs.
- [ ] Tests: unit and integration with a fake email sender at the system boundary; contract; expired, reused and wrong tokens.
- [ ] `docs/design/flows.md` Analytics gains `password_reset_requested` (no properties) and `password_reset_completed` (no properties). They are sent by the app in the mobile follow-up card.
- [ ] ADR-015: the provider key is read from `/run/secrets/email_provider_api_key`, mounted only into the service that sends email (`root:<its GID>` 0440 on Linux); `env-init.sh` creates it empty and prints the file to fill, never a value; CI uses a dummy.

## Allowed files

- `contracts/openapi.yaml`, `apps/api/modules/auth/**`, `apps/api/core/**`, `apps/api/migrations/**`, `apps/api/pyproject.toml`, `apps/api/uv.lock`, `apps/api/tests/**`
- `docs/adr/0xx-*.md`, `docs/adr/README.md`, `docs/design/flows.md` (Analytics table only), `infra/compose/env-init.sh`
- ADR-015: `infra/compose/compose.base.yml` (`email_provider_api_key` secret entry and the sending service's `secrets:` list only); `docs/runbooks/secret-leak.md` (email-provider row)

## Out of scope

- Mobile reset screens. File a mobile card with a design spec when this card is planned.
- Email verification at sign-up (not decided; ask the owner if needed). Marketing email.

## Analytics events

- none server-side. It defines `password_reset_requested` and `password_reset_completed` for the mobile follow-up.

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 on the owner's decision: E1 sends no email; password reset with a free-tier email service comes before external beta, with no dependency on the E1 demo.
- Numbers:
- Left for later:
  - A mobile card for the reset screens (needs a product-designer spec).
