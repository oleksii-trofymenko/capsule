---
name: mobile-screen
description: Build an Expo screen from an approved design spec with all states, accessibility and tests. Use for any new or changed screen in apps/mobile.
---

# Mobile screen

1. **Spec.** Open the design spec the card links. No spec → stop and ask the Orchestrator for `product-designer`.
2. **Route.** Add the screen under `app/` (Expo Router); feature logic under `features/<feature>/`.
3. **Data.** Use the generated API client with a TanStack Query hook. Define the cache key, stale time and offline behaviour.
4. **States.** Implement loading (skeleton), empty, error (with retry) and offline, each with the copy from the spec.
5. **Tokens.** Colours, type, spacing, radius and shadow come from the design tokens. No raw hex values in components.
6. **Accessibility.** `accessibilityLabel` on icon buttons, roles on custom controls, touch targets ≥ 44 pt / 48 dp, text scales with Dynamic Type, contrast AA.
7. **Performance.** Lists use FlashList; animations use Reanimated; no heavy work on mount.
8. **Platform feel.** Native back gesture, safe areas, keyboard avoidance, light and dark appearance if the spec has both.
9. **Tests.** RNTL tests for state switching and interactions; a Maestro flow if the screen is on a critical path.
10. **Evidence.** Screenshots of every state on iOS and Android in the PR, for the design review.
