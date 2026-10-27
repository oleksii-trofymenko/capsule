# E1-12 · Mobile: navigation shell, silent guest start, session handling

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | mobile-engineer |
| Reviewers | code-reviewer, security-engineer, product-designer |
| Estimate | M |
| Metric | Activation rate (no sign-up gate before the first guide) |
| Depends on | E1-05, E1-05c, E1-18 |
| ADRs | 001, 002, 003, 014 |
| Design spec | `docs/design/flows.md` (F6 "Guest data"), `docs/design/onboarding-wireframes.md` (no sign-in on Welcome) |

## Why

As a new user, I want the app to work the moment I open it, without an account, so that I can try Capsule before giving any personal details.

## Acceptance criteria

- [ ] Expo Router navigation shell with a placeholder home and a header menu that has an entry for sign-in/sign-up (screens in E1-13) and Settings (E1-14).
- [ ] First launch: the app gets a guest credential silently and stores it only in `expo-secure-store` (`AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY`), through `shared/storage`. The user sees nothing.
- [ ] The API client (generated from the contract) adds the access token, refreshes once on 401 with rotation, and avoids parallel refreshes (one refresh in flight at a time). If refresh fails, it falls back to a new guest credential and keeps the old account tokens out of storage.
- [ ] A 503 from refresh is retried after `Retry-After` and never signs the user out or drops the tokens (E1-05c).
- [ ] R6 (client side, `docs/security.md`): a retry after a lost refresh response follows the ADR-014 grace rule. Single-flight refresh alone does not cover this. Tested.
- [ ] P2: the first launch after a reinstall wipes secure-store and MMKV (ADR-003), using `wipeAll()` from E1-18.
- [ ] P5: the app carries only non-secret `EXPO_PUBLIC_*` values (the API base URL). The bundle scan is E8-02.
- [ ] The API base URL comes from env (`EXPO_PUBLIC_*`), so the quick-tunnel URL changes with no code change (E1-15).
- [ ] P1: no token or credential in logs, Sentry breadcrumbs or MMKV.
- [ ] A typed `track()` in `shared/analytics` records the E1 events. It sends nothing until consent and PostHog are wired (E2/E3); tests check the calls.
- [ ] Tests (Jest + RNTL):
  - [ ] Silent guest start.
  - [ ] Refresh on 401, with two parallel requests.
  - [ ] A failed refresh leads to a new guest.
  - [ ] Reinstall wipe.
  - [ ] Offline first launch shows the offline state and retries.

## Allowed files

- `apps/mobile/app/**`, `apps/mobile/shared/**`, `apps/mobile/features/profile/**`, `apps/mobile/package.json`, `apps/mobile/package-lock.json`, `apps/mobile/app.config.*`, `apps/mobile/.env.example`
- `apps/mobile/**/__tests__/**`

## Out of scope

- Onboarding O1–O5 and consent (E3). Sign-up and sign-in screens (E1-13). PostHog and Sentry SDKs (E2).

## Analytics events

- `app_opened` — cold start, or foreground after ≥ 30 min in the background — `is_guest`. Recorded through `track()`; nothing is sent until consent exists.

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan. Added the dependency on E1-18 because `apps/mobile` has no Expo project yet.
  - 2026-10-27: amended from E1-01 threat model (docs/security.md).
- Numbers:
- Left for later:
