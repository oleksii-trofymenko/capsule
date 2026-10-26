# E0-08 · Personas, user flows and MVP wireframes

| Field | Value |
| --- | --- |
| Status | done |
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

- [x] Before the agent starts (you): export the canvas artboards as PNG into `docs/design/reference/` — the canvas is private and agents cannot open it.
- [x] `docs/design/personas.md`: four personas covering men and women, ages ~25, ~40 and ~55, different budgets and events. No stereotypes; each has a goal and a frustration.
- [x] `docs/design/flows.md`: onboarding (wardrobe choice: menswear, womenswear, unisex; style; sizes), ask → follow-up → guide, photo, voice, saved guides, offline. Each step lists its screen and its states.
- [x] Wireframes for onboarding (not yet on the canvas); chat and guide reference the existing canvas.
- [x] Copy deck for onboarding and empty, error and offline states in en-GB.
- [x] Accessibility notes per screen (labels, focus order, Dynamic Type behaviour).
- [x] Analytics events agreed with product-analyst for the activation funnel.

## Allowed files

- `docs/design/**`
- `docs/metrics.md` (product-analyst: guest-first metric definitions) and `docs/blueprint.md` (§1, §7, §10, §11 lines changed by the owner's decisions), added 2026-10-26 with the owner's approval

## Out of scope

- High-fidelity visual design of new screens; mobile code.

## Analytics events

- As agreed in `docs/design/flows.md` → Analytics. Key events: `app_opened`, `onboarding_started`, `onboarding_completed` (wardrobe, has_style, has_sizes), `consultation_started` (input), `guide_delivered` (guide_id, latency_ms, within_budget, is_first, since_onboarding_ms), `guide_feedback`, `signup_prompt_shown`, `signup_started`, `signup_completed`.

## Notes (filled while working)

- Plan approved: 2026-10-26 by the owner (product-designer plan).
- Decisions:
  - Reference screens: the owner chose to let agents use the local canvas export (`AI Stylist — Chat & Guide.html`, gitignored). The Orchestrator rendered it at 2x with headless Chrome into seven PNGs in `docs/design/reference/`; checked before commit — placeholders only, no people or personal data.
  - Owner: sign-up comes AFTER the first guide (guest first; offered on "Save guide"). Wardrobe = Menswear / Womenswear / Unisex + "Skip for now". The guide's wardrobe toggle becomes a label + "Change" that starts a new guide.
  - Owner: blueprint §1 updated to guest-first metrics; sign-up conversion target set after 4 weeks of beta (baseline first).
  - Fixes to the reference screens: photo-deletion copy matches ADR-008 ("deleted once processed, always within 24 hours"); body-shape line removed; "Capsule · AI stylist" disclosure; 👍/👎 added; no media kept on the phone (no voice playback, photo becomes text after upload); "Checked by code" → plain budget wording.
  - Consent (security-engineer): two opt-in switches, both off — Crash reports (Sentry, ePrivacy Art. 5(3)) and Usage events (PostHog); equal buttons; neither SDK starts before the choice. Crash-free and app-start metrics cover consenting users only.
  - Guest data requirements for E1 written into flows.md (guest credential in secure-store; retention N days after last activity, upper bound in an E1 ADR, 30 proposed; "Delete my data" server-first; move to account only at sign-up/sign-in). "Save on this phone" replaces "Keep on this phone only".
  - Analytics agreed with product-analyst (`app_opened`, `guide_id`, `guide_feedback_reason`, `guide_failed`, `wardrobe_changed`, `signup_started` added); `docs/metrics.md` updated (activation from `onboarding_started`, time to first guide via `since_onboarding_ms`, sign-up conversion).
  - Wireframes are ASCII box layouts in markdown (diffable, readable by text-only reviewers). No auto-advance in onboarding (screen-reader and switch users): 6 taps with every optional step skipped.
  - PR exceeds the ~400-line guideline (~1,000 lines of docs + 7 PNGs); code-reviewer advised against splitting because the files cross-reference copy and screen ids.
- Reviews: code-reviewer request changes (3 copy-id gaps, incl. over-budget state) → fixed → approve (after allowed files were extended). product-analyst changes → applied → agree. security-engineer request changes (HIGH: guest data unspecified; Sentry opt-in) → fixed → approve. Docs only: no QA run.
- Numbers: 4 personas; 10 flows (F1–F10); 11 wireframed screens/sheets; ~290 copy ids, every id referenced and every reference defined (3 documented exceptions); 7 reference PNGs.
- Left for later:
  - E1: guest credential, retention ADR (N days), "Delete my data" and export, move-to-account.
  - E2: identity across sign-up (same distinct id; account-stored random analytics id); verify Sentry per-id deletion on the free plan, else amend ADR-004 and the delete copy.
  - E3: durable storage for phone-only saved guides (separate MMKV key enough, or an ADR); usability test with ≥ 5 people of different genders and ages before chat/guide are built.
  - Blueprint §11 smoke flow and §10 Stability row were aligned here; the owner's private blueprint should get the same changes.
