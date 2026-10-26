# E0-08 · Personas, user flows and MVP wireframes

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | product-designer |
| Reviewers | product-analyst, you |
| Estimate | M |
| Metric | Activation rate |
| Depends on | E0-01 |
| ADRs | none |
| Design spec | `docs/design/reference/*.png` (exported from the "AI Stylist — Chat & Guide" canvas: chat, guide, streaming, offline) |

## Why

Activation depends on the first five minutes: onboarding and the first guide. Flows must be agreed before any screen is built.

## Acceptance criteria

- [ ] Before the agent starts (you): export the canvas artboards as PNG into `docs/design/reference/` — the canvas is private and agents cannot open it.
- [ ] `docs/design/personas.md`: four personas covering men and women, ages ~25, ~40 and ~55, different budgets and events. No stereotypes; each has a goal and a frustration.
- [ ] `docs/design/flows.md`: onboarding (wardrobe choice: menswear, womenswear, unisex; style; sizes), ask → follow-up → guide, photo, voice, saved guides, offline. Each step lists its screen and its states.
- [ ] Wireframes for onboarding (not yet on the canvas); chat and guide reference the existing canvas.
- [ ] Copy deck for onboarding and empty, error and offline states in en-GB.
- [ ] Accessibility notes per screen (labels, focus order, Dynamic Type behaviour).
- [ ] Analytics events agreed with product-analyst for the activation funnel.

## Allowed files

- `docs/design/**`

## Out of scope

- High-fidelity visual design of new screens; mobile code.

## Analytics events

- `onboarding_started`, `onboarding_completed` (wardrobe, has_sizes), `consultation_started` (input: text, voice, photo), `guide_delivered` (latency_ms, within_budget)

## Notes (filled while working)

- Plan approved:
- Decisions:
- Numbers:
- Left for later:
