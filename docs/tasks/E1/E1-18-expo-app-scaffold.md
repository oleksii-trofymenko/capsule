# E1-18 · Expo app scaffold: dev build, storage layer, generated API client

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | mobile-engineer |
| Reviewers | code-reviewer, security-engineer (dependencies) |
| Estimate | M |
| Metric | Mobile cold start < 2 s (release build, mid-range Android); the empty-app baseline is recorded here |
| Depends on | none (E1-05 for the first real generated types; the generator can run on the current contract) |
| ADRs | 001, 002, 003, 016, 018, 019; a new ADR for the API-client generator if neither blueprint §4 nor an accepted ADR names one |
| Design spec | none (no screens beyond a placeholder) |

## Why

`apps/mobile` has only lint config and `CLAUDE.md`, so there is no Expo project yet. Every E1 mobile card needs a project that builds, a `shared/storage` layer that enforces ADR-003, and API types generated from the contract. The `unit (mobile)` and `audit (mobile)` CI jobs already skip until `package.json` exists.

## Acceptance criteria

- [ ] An Expo project in `apps/mobile`, as ADR-001 requires: TypeScript strict, Expo Router, New Architecture, `expo-dev-client`. The development build runs on the Android emulator (Windows PC) and the iOS Simulator (laptop), with steps in the runbook.
- [ ] TanStack Query and Zustand wired (ADR-002).
- [ ] `shared/storage`:
  - [ ] The only access to `expo-secure-store` (`AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY`) and MMKV.
  - [ ] MMKV is excluded from OS backups.
  - [ ] A `wipeAll()` for logout, deletion and reinstall.
  - [ ] A lint rule or test stops direct imports of either module elsewhere.
- [ ] P1 (`docs/security.md`), the part missing above: secure-store data is also kept out of OS backup, including Android Auto Backup, and `shared/storage` offers no way to write a credential to MMKV.
- [ ] API types are generated from `contracts/openapi.yaml` by a script. CI fails if the generated files are stale.
- [ ] Jest + RNTL configured. `npm test` runs in the existing `unit (mobile)` job, `npm audit` passes in `audit (mobile)`, and the pre-commit hooks (ESLint, Prettier, tsc) pass.
- [ ] Baseline numbers recorded: cold start of the empty release build on a mid-range Android, and APK size.
- [ ] Tests: unit tests for `shared/storage` (secure-store vs MMKV routing, `wipeAll`).

## Allowed files

- `apps/mobile/**` (except `CLAUDE.md`), `.github/workflows/ci.yml` (only the mobile jobs and the stale-types check), `docs/runbooks/mobile-dev-build.md` (new), `docs/adr/0xx-*.md` and `docs/adr/README.md` (only for the generator ADR)

## Out of scope

- Design tokens, fonts and UI primitives (E1-19). Screens (E1-12 onwards). EAS cloud builds and store setup (E8). Sentry and PostHog (E2).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27, added to the approved E1 plan: the plan assumed an Expo project existed, but `apps/mobile` has none.
  - 2026-10-27 (owner): UI is tested on the Android emulator (Windows PC) and the iOS Simulator (laptop). No physical iPhone build, so no paid Apple Developer account. The mid-range Android cold-start baseline waits for a real device; record the emulator number as indicative.
  - 2026-10-27: amended from E1-01 threat model (docs/security.md). Coverage of P1 and P2:
    - P1 is shared with E1-12. Here, the `shared/storage` criteria (secure-store `AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY` as the only access, MMKV excluded from backup, no direct imports) cover it, plus the added P1 criterion for secure-store backup exclusion and no credentials in MMKV. E1-12 covers "nothing in logs or breadcrumbs".
    - P2 is shared with E1-12. Here, `wipeAll()` clears both stores; E1-12 calls it on the first launch after install.
- Numbers:
- Left for later:
