# apps/mobile — Expo (React Native) app

Read the root `CLAUDE.md` first. This file adds mobile rules.

## Shape

- `app/` — screens (Expo Router). `features/` — chat, onboarding, guide, profile. `shared/` — UI kit, generated API client, storage. `e2e/` — Maestro flows.
- UI is built from the product designer's specs only. No screen without an approved design.

## Rules

- TypeScript strict, no `any`. API types are generated from `contracts/openapi.yaml`, never hand-written.
- Server state: TanStack Query; offline history and queued messages are the persisted query cache (ADR-002). Local state: Zustand.
- Storage (ADR-003): tokens and other credentials in `expo-secure-store` only (`AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY`); query cache and settings in MMKV (no credentials, no photos, excluded from backup); expo-sqlite deferred; all access through `shared/storage`. Never in logs or Sentry breadcrumbs. No photo or voice file is kept on the device after upload succeeds.
- Run as a development build (expo-dev-client), not Expo Go; New Architecture only (ADR-001).
- Sentry and PostHog start only after their own consent switch is on, with no session replay, screenshots or autocapture (ADR-004, `docs/design/flows.md`).
- Keep the JS thread free: Reanimated for animation, FlashList for long lists, memoise only where a measurement shows a problem.
- Every screen handles loading, empty, error and offline states.
- Accessibility: labels on icon buttons, touch targets ≥ 44 pt (iOS) / 48 dp (Android), Dynamic Type, contrast WCAG AA.
- Ask for camera, microphone and photo permissions at the moment of use, with a reason.
- Compress photos to ≤ 1 MB on device before upload; strip EXIF.
- A new dependency: check bundle size, Expo and New Architecture support, and add an ADR unless blueprint §4 or an accepted ADR names it. Gradients, `react-native-svg`, the icon set and `expo-font` come with the E1 "UI rendering primitives" ADR (E0-09).

## Visual direction (tokens: `docs/design/tokens.json`, components: `docs/design/components.md` — they win over this summary)

- Font: Plus Jakarta Sans.
- Brand gradient: #BF4A33 → #7A3E9D (135°), used on primary buttons, user bubbles, selected chips.
- Background: #FFF5EE → #FBEAE3 → #F4E4EF (top to bottom).
- Text: #1E1A24 primary, #4F4855 secondary, #675F6C muted.
- Bubbles with tails; soft plum-tinted shadows; unselected controls keep a visible 1 px `border.control` (WCAG 1.4.11).
- Reference mockups: PNG exports in `docs/design/reference/` (added in E0-08). The source canvas is private to the project owner.

## Targets

Cold start < 2 s (release build, mid-range Android) · 60 fps, < 1% slow frames · crash-free sessions > 99.5%.

## Tests

Jest + React Native Testing Library for component logic; Maestro for critical flows (onboarding, ask → guide, offline).
