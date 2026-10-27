# E1-19 · UI rendering primitives ADR and design tokens in the app

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | mobile-engineer (drafts the ADR with the `adr` skill; the owner accepts) |
| Reviewers | code-reviewer, product-designer, security-engineer (dependencies) |
| Estimate | M |
| Metric | Decisions on record (every stack choice has an accepted ADR) |
| Depends on | E1-18 |
| ADRs | new ADR "UI rendering primitives" (promised in E0-09 and `docs/design/components.md` Open questions 1) |
| Design spec | `docs/design/tokens.json`, `docs/design/components.md` |

## Why

E0-09 left one E1 decision open: how gradients, SVG, icons and the Plus Jakarta Sans font are rendered. The first E1 screens (A2, S1) cannot follow the design system without it, and tokens have to exist in code with a guarantee that they match `tokens.json`.

## Acceptance criteria

- [ ] The ADR is accepted by the owner. It decides, with alternatives (components.md Open questions 1):
  - [ ] Gradients: `expo-linear-gradient` or the built-in `experimental_backgroundImage`.
  - [ ] `react-native-svg`.
  - [ ] The icon set (Lucide proposed, 2 px stroke).
  - [ ] `expo-font` with the config plugin and the bundled OFL font files and licence.
  - [ ] A dependency-free token generator, or a hand-kept `tokens.ts` with a parity test.
- [ ] Tokens are available in `shared/ui` for light and dark themes. A test fails if any value differs from `docs/design/tokens.json`.
- [ ] Plus Jakarta Sans is embedded at build time (no runtime loading) and the OFL licence ships with the app.
- [ ] Cold start re-measured against the E1-18 baseline; any change is recorded.
- [ ] Tests: the token parity test; a render test showing the font and theme switch.

## Allowed files

- `apps/mobile/shared/ui/**`, `apps/mobile/assets/fonts/**`, `apps/mobile/app.config.*`, `apps/mobile/package.json`, `apps/mobile/package-lock.json`, `apps/mobile/**/__tests__/**`
- `docs/adr/0xx-ui-rendering-primitives.md`, `docs/adr/README.md`

## Out of scope

- Building components (E1-20). Changing `tokens.json` or `components.md`.
- Shadow profiling in long lists (E3, when lists exist).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27, added to the approved E1 plan: the ADR and the tokens-in-app work were promised to E1 by E0-09.
- Numbers:
- Left for later:
