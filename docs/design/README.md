# Design specs

Specs the mobile app is built from. No screen is built without one (`apps/mobile/CLAUDE.md`). Card: `docs/tasks/E0/E0-08-design-flows.md`.

| File | What |
| --- | --- |
| [personas.md](personas.md) | Four personas used to check flows, copy and evals |
| [flows.md](flows.md) | Every flow, step by step: screen, states, accessibility, analytics |
| [onboarding-wireframes.md](onboarding-wireframes.md) | Low-fidelity wireframes for onboarding, guest sign-up, saved guides and sheets (not on the canvas) |
| [copy-deck.md](copy-deck.md) | All en-GB strings for these flows, with ids |
| [tokens.json](tokens.json) | Design tokens (W3C DTCG): primitive palette, theme-independent scales (`base`), light and dark semantic themes. The only source of colour, type, spacing, radius, shadow and motion for the app (E0-09) |
| [components.md](components.md) | Base components with every state, the flows → components coverage table and the WCAG contrast table for both themes (E0-09) |
| [reference/](reference/) | Exports of the owner's canvas: [chat](reference/01-chat.png), [guide](reference/02-guide.png), [generating](reference/03-state-generating.png), [offline](reference/04-state-offline.png), and three story slides ([ask](reference/05-slide-1-ask.png), [photo](reference/06-slide-2-photo.png), [guide](reference/07-slide-3-guide.png)) |

## How to read

- **Screen ids** (`O1`, `C2`, `G1` …) are defined in `flows.md` and reused in the wireframes and copy deck.
- **Copy ids** (`onb.wardrobe.title`) are defined in `copy-deck.md`. Specs quote the id, not the text, so copy changes in one place.
- **Reference PNGs** show the visual direction. Where a spec and a PNG disagree, the spec wins; the differences are listed in `flows.md` → "Changes from the reference screens".
- **Wireframes** are ASCII boxes inside markdown so they diff line by line in a PR and can be reviewed without a design tool. They fix layout, order and content, not visual style. Colours, type and spacing come from the tokens (E0-09).

## Rules every spec follows

- Neutral brand. Wardrobe (menswear, womenswear, unisex) is chosen by the user, never inferred from a photo, a name or a voice.
- Capsule never comments on bodies or appearance. Photos are described by clothes, colours and fit only.
- Every screen states loading, empty, error and offline behaviour.
- Touch targets ≥ 44 pt / 48 dp; every icon button has a label; Dynamic Type up to 200 % without loss of content; WCAG AA contrast; voice is an equal input.
- No analytics event before the user chooses on the consent screen (ADR-004). No free text, sizes, photos or event descriptions in any event property.
- Copy never promises more than the ADRs guarantee (media deletion: ADR-008).
