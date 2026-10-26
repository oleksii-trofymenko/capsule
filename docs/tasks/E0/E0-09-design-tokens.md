# E0-09 · Design tokens and base components spec

| Field | Value |
| --- | --- |
| Status | done |
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

- [x] `docs/design/tokens.json`: colour (brand gradient #BF4A33 → #7A3E9D, background gradient, text primary, secondary, muted, surfaces, status), type scale (Plus Jakarta Sans), spacing (4-pt scale), radius, shadows, light theme; dark theme values or an explicit "later" decision.
- [x] Every text/background pair used in the canvas meets WCAG AA; contrast values listed next to the pair.
- [x] `docs/design/components.md`: spec for button (primary gradient, secondary, icon), chip (selected, unselected), message bubble with tail (user, stylist), guide item card, budget bar, banner (offline, error), input bar. States: default, pressed, disabled, focus.
- [x] Token names are platform-neutral and map one-to-one to what mobile-engineer will import.

## Allowed files

- `docs/design/**`

## Out of scope

- Implementing tokens in the app (first mobile card in E1).

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-26 by the owner (product-designer plan).
- Decisions:
  - Owner: Plus Jakarta Sans everywhere (weights 400–800, embedded at build time with the expo-font config plugin, OFL licence bundled; no runtime loading). Dark theme values now. Small accent text uses #A13F2B (already in the canvas); #BF4A33 stays for gradients, icons and large text. Body text 16/24 instead of the canvas 15/22. Visible 1 px `border.control` (#8A8290) on unselected controls (WCAG 1.4.11).
  - Values come from the canvas itself: the Orchestrator decoded the compressed bundle in the local canvas HTML and extracted every CSS value with counts (viewer-chrome values ignored). #8A8290 is never used for text (3.0–3.7:1).
  - Format: W3C DTCG draft — `primitive` (hues, never used by components), `base` (theme-independent: font faces, text styles, space, radius, size, motion), `semantic.light` / `semantic.dark` (identical keys, aliases only). Mobile imports `theme[scheme].<group>.<token>` and `base.<group>.<token>`; text styles are leaf tokens mapping to RN style keys; `fontFamily` = per-weight face (PostScript names), `fontWeight` documentation only. Style Dictionary is a format note, not a tooling commitment.
  - Status never by colour alone (icon + text everywhere); no red/green pair. Disabled = solid surface with passing text, not an opacity fade. Pressed on gradient = dark overlay. Focus: Android outline ring; iOS system focus effect. Selected radio row uses `border.selected`, distinct from focus.
  - Removed from the canvas: header blur (needs a dependency), avatars beside bubbles. Touch targets raised to 44 visual / 48 hit; smallest text 12; spacing snapped to 4 pt; 17 radii → 6.
  - Picker and Android action sheet reuse our own bottom sheet (no dependency); native `formSheet` accepted.
  - PR is ~1,200 lines of docs and token data; reviewers advised keeping it as one PR (parts depend on each other).
- Reviews: code-reviewer approve (11 suggestions → applied) → approve. mobile-engineer request changes (font faces, lineHeight note, tail anchor, iOS focus) → fixed → approve. Docs only: no QA run.
- Numbers: 311 tokens; light and dark 58 semantic keys each; 113 contrast pairs listed, every one verified by script (match within 0.02; none marked pass below threshold). Worst passing text pair: white on #BF4A33 4.95; muted text on #F4E4EF 5.01.
- Left for later:
  - E1: one "UI rendering primitives" ADR — gradients (`expo-linear-gradient` vs built-in `experimental_backgroundImage`), `react-native-svg` (bubble tail, icons), icon set (Lucide proposed, 2 px stroke), `expo-font` + Plus Jakarta Sans OFL files; a dependency-free token generator or hand-kept `tokens.ts` with a parity test.
  - E1 profiling: multi-layer `boxShadow` in long lists; `singleLayerFallback` if slow frames > 1 %. Confirm `tnum` support before using tabular figures.
  - E3 usability test: include at least one dark-theme participant and one at 200 % text.
  - Cosmetic: the photo-upload progress bar reuses `size.budgetBarHeight` (a neutral name would read better).
