# E1-20 · Base components for A2 and S1

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | mobile-engineer |
| Reviewers | code-reviewer, product-designer |
| Estimate | M |
| Metric | Frame rate: 60 fps, < 1% slow frames |
| Depends on | E1-19, E1-11 |
| ADRs | the UI rendering primitives ADR (E1-19) |
| Design spec | `docs/design/components.md` (Button, Form controls, Sheets/dialogs/toasts, Header, Banner, and the text field added by E1-11) |

## Why

A2 and S1 need buttons, a text field, a checkbox row, a dialog, a toast and a header that match the design system and accessibility rules. Building them once here keeps the screen cards (E1-13, E1-14) within a day.

## Acceptance criteria

- [ ] In `shared/ui`, each built to its components.md spec:
  - [ ] Primary and secondary Button, plus Icon button.
  - [ ] Text field (including secure entry).
  - [ ] Checkbox row.
  - [ ] Dialog and toast.
  - [ ] Header with menu.
  - [ ] Error banner.
- [ ] Every component has default, pressed, disabled and focus states (plus loading/error where specified), uses semantic tokens only, and works in dark theme.
- [ ] Accessibility: roles, labels and `accessibilityState`; touch targets ≥ 44 pt / 48 dp; font scaling up to `base.font.scale.max`; Reduce Motion respected. Status never relies on colour alone.
- [ ] Only the components listed above. Nothing for chat or guide screens.
- [ ] Tests: Jest + RNTL for states and a11y props of each component. A screenshot of each in light and dark goes in the PR for product-designer review.

## Allowed files

- `apps/mobile/shared/ui/**`, `apps/mobile/**/__tests__/**`

## Out of scope

- Chips, bubbles, guide cards and other E3 components. Screens (E1-13, E1-14).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27, added to the approved E1 plan so E1-13 and E1-14 stay M.
- Numbers:
- Left for later:
