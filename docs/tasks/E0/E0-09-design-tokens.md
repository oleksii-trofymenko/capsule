# E0-09 · Design tokens and base components spec

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | product-designer |
| Reviewers | mobile-engineer, you |
| Estimate | M |
| Metric | Helpful rate (consistency of the guide UI) |
| Depends on | E0-01 |
| ADRs | none |
| Design spec | `docs/design/reference/*.png` (from E0-08) and the values in `apps/mobile/CLAUDE.md` |

## Why

The mobile app must read colours, type and spacing from one source, so no screen invents its own values and the brand stays consistent.

## Acceptance criteria

- [ ] `docs/design/tokens.json`: colour (brand gradient #BF4A33 → #7A3E9D, background gradient, text primary, secondary, muted, surfaces, status), type scale (Plus Jakarta Sans), spacing (4-pt scale), radius, shadows, light theme; dark theme values or an explicit "later" decision.
- [ ] Every text/background pair used in the canvas meets WCAG AA; contrast values listed next to the pair.
- [ ] `docs/design/components.md`: spec for button (primary gradient, secondary, icon), chip (selected, unselected), message bubble with tail (user, stylist), guide item card, budget bar, banner (offline, error), input bar. States: default, pressed, disabled, focus.
- [ ] Token names are platform-neutral and map one-to-one to what mobile-engineer will import.

## Allowed files

- `docs/design/**`

## Out of scope

- Implementing tokens in the app (first mobile card in E1).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
- Numbers:
- Left for later:
