# apps/mobile — Expo (React Native) app

Read the root `CLAUDE.md` first. This file adds mobile rules.

## Shape

- `app/` — screens (Expo Router). `features/` — chat, onboarding, guide, profile. `shared/` — UI kit, generated API client, storage. `e2e/` — Maestro flows.
- UI is built from the product designer's specs only. No screen without an approved design.

## Rules

- TypeScript strict, no `any`. API types are generated from `contracts/openapi.yaml`, never hand-written.
- Server state: TanStack Query. Local state: Zustand. Tokens: `expo-secure-store` only — never AsyncStorage, logs or Sentry breadcrumbs.
- Keep the JS thread free: Reanimated for animation, FlashList for long lists, memoise only where a measurement shows a problem.
- Every screen handles loading, empty, error and offline states.
- Accessibility: labels on icon buttons, touch targets ≥ 44 pt (iOS) / 48 dp (Android), Dynamic Type, contrast WCAG AA.
- Ask for camera, microphone and photo permissions at the moment of use, with a reason.
- Compress photos to ≤ 1 MB on device before upload; strip EXIF.
- A new dependency: check bundle size and Expo support, and add an ADR.

## Current visual direction (until tokens land in E0-09)

- Font: Plus Jakarta Sans.
- Brand gradient: #BF4A33 → #7A3E9D (135°), used on primary buttons, user bubbles, selected chips.
- Background: #FFF5EE → #FBEAE3 → #F4E4EF (top to bottom).
- Text: #1E1A24 primary, #4F4855 secondary, #675F6C muted.
- Bubbles with tails; soft plum-tinted shadows instead of borders.
- Reference mockups: PNG exports in `docs/design/reference/` (added in E0-08). The source canvas is private to the project owner.

## Targets

Cold start < 2 s (release build, mid-range Android) · 60 fps, < 1% slow frames · crash-free sessions > 99.5%.

## Tests

Jest + React Native Testing Library for component logic; Maestro for critical flows (onboarding, ask → guide, offline).
