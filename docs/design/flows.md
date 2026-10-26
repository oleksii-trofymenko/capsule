# User flows (MVP)

Card: `docs/tasks/E0/E0-08-design-flows.md` · Metric: activation rate · Personas: `personas.md` · Copy: `copy-deck.md` · Wireframes: `onboarding-wireframes.md` · Visual reference: `reference/*.png`.

Each step names its screen and its states. Copy is quoted by id from `copy-deck.md`. Accessibility notes sit under each screen; the rules that apply everywhere are in "Global" below.

## Screen index

| Id | Screen | Source |
| --- | --- | --- |
| O1 | Welcome | Wireframe |
| O2 | Analytics consent | Wireframe |
| O3 | Wardrobe | Wireframe |
| O4 | Style | Wireframe |
| O5 | Sizes | Wireframe |
| C1 | Chat (ask, follow-up, photo, voice) | `reference/01-chat.png`, `05-slide-1-ask.png`, `06-slide-2-photo.png` + wireframe for the first-run empty state |
| C2 | Chat, generating | `reference/03-state-generating.png` |
| C3 | Chat, offline | `reference/04-state-offline.png` |
| G1 | Guide | `reference/02-guide.png`, `07-slide-3-guide.png` (with the changes listed at the end) |
| A1 | Save sheet (guest → sign-up) | Wireframe |
| A2 | Sign-up / sign-in | E1 card; this spec only sets entry, exit and copy around it |
| L1 | Saved guides | Wireframe |
| P1 | Permission reason sheet (camera, photos, microphone) | Wireframe |
| S1 | Settings: wardrobe, style, sizes, privacy | Out of scope here; entries listed in F9 |

## Global

These apply to every screen and are not repeated below.

- **Header:** assistant name is always "Capsule" with subtitle `chat.header.subtitle` ("AI stylist") or a live status (`chat.status.*`). Never "Stylist" alone, never "online": the user must know they are talking to software.
- **Offline:** a banner (`offline.banner`) at the top of content, announced once by the screen reader. Cached content stays usable; actions that need the network are disabled with a reason, not hidden.
- **Server unreachable** (online but API down or timed out): inline error with "Try again" (`error.server.*`). Never a blank screen, never a raw error code.
- **Loading:** skeletons for content that has a known shape (guide, saved list); a status line for work in progress (chat). No spinner-only screens longer than 1 s.
- **Accessibility:**
  - Every icon button has a label (`a11y.*` in the copy deck) and a 44 pt / 48 dp target, even when the icon is 24 pt.
  - Dynamic Type / font scale up to 200 %: text wraps, never truncates mid-word in headings or prices; chip groups wrap to new lines; side-by-side rows (name + price, budget label + amount) stack vertically above 150 %.
  - Reduce Motion: typing dots, streaming caret and step spinners become static; status is still announced.
  - Focus order follows reading order: header, content top to bottom, then composer or primary button.
  - Status changes (offline, queued, sent, guide ready) are announced as polite live-region updates, not alerts.
  - Selected chips expose "selected" state, not only colour; the tick icon is decorative.
  - Contrast is verified against WCAG AA when tokens land (E0-09), including white text on both ends of the brand gradient and muted text on the lightest background.

## F1 · Onboarding (first launch)

Goal: reach the first ask in ≤ 5 taps. Style and sizes are optional so time to first guide stays under 90 s (p95). Nothing here creates an account: the user continues as a guest (F6).

| Step | Screen | What happens | States |
| --- | --- | --- | --- |
| 1 | O1 Welcome | Value in one line, three bullets (ask, reuse, budget). Primary: "Get started". | Offline: still shown; banner says a connection is needed for the first guide. |
| 2 | O2 Consent | Usage analytics choice. "Allow" and "Not now" have equal visual weight. Nothing is sent before a choice. | Either choice continues. Choice stored on device; changeable in Settings → Privacy. |
| 3 | O3 Wardrobe | Menswear, Womenswear, Unisex (single select) or "Skip for now". | Nothing selected: "Continue" disabled, "Skip for now" always enabled. |
| 4 | O4 Style | Up to 3 style chips, or "Not sure yet". | Optional. Skip continues. |
| 5 | O5 Sizes | Tops, bottoms, shoes; size system EU / UK / US. | Optional ("Skip for now"). Partial entry is fine. |
| 6 | C1 Chat, first run | Empty-state greeting and three example prompts that cover menswear, womenswear and unisex events. | See F2. |

Back is available on O3–O5. Choices are kept if the user goes back. Killing the app mid-onboarding resumes at the last unfinished step.

### O1 Welcome — accessibility
- Heading is the first focus. Illustration (if any) is decorative and hidden from the screen reader; it must not show people.

### O2 Consent — accessibility
- Both buttons ≥ 48 dp tall, full width, stacked; "Allow" first, "Not now" second, same size and style weight (one filled, one outlined is acceptable only if both pass AA; no grey "dark pattern" link).
- "What we collect" is a real button that expands inline, not a tiny link.

### O3 Wardrobe — accessibility
- Options are a radio group (role = radiogroup), each option a full-width row ≥ 56 pt with label and one-line description.
- Helper text (`onb.wardrobe.helper`) is read after the title, before the options.

### O4 Style — accessibility
- Chips are checkboxes; the screen reader says "2 of 3 selected". When 3 are chosen, other chips are announced as "unavailable, maximum 3".

### O5 Sizes — accessibility
- Each size is a labelled picker ("Tops size, EU, not set"). No free-text size fields. Size system is a segmented control with 3 labelled segments.
- Copy speaks about sizes "you usually buy", never about body.

## F2 · Ask → follow-up → guide

| Step | Screen | What happens | States |
| --- | --- | --- | --- |
| 1 | C1 | User describes event and budget by text, voice (F4) or photo (F3). | Empty (first run): greeting + example prompts. Composer empty: send disabled, mic enabled. Offline: text is queued (F8). |
| 2 | C1 | Capsule asks only what it still needs, as chips plus free reply. If wardrobe was chosen in onboarding it is **not** asked again; the header shows it and "Change" opens F9. If wardrobe was skipped, Capsule asks once here (`chat.followup.wardrobe`), and the answer is saved to the profile. | Typing indicator while Capsule prepares the question (`chat.status.thinking`). Error: `error.server.*` with "Try again" on the failed message. |
| 3 | C2 | Generating: progress steps (understood request, read photo, found pieces, checked budget, writing guide), then the guide streams in. "Stop" is available. Composer stays active (`chat.composer.placeholder_busy`). | Stopped: partial guide is discarded; message `chat.stopped` with "Try again". Timeout > 60 s: `error.guide.timeout`. No look fits budget: `error.guide.no_fit` with options (F5). |
| 4 | G1 | Guide card in chat; tap opens full guide. | See F5. |

### C1 Chat — accessibility
- Composer order: camera, text field, microphone, send. Labels: `a11y.camera`, `a11y.mic`, `a11y.send`. Menu and new-chat icons in the header: `a11y.menu`, `a11y.new_chat`.
- Each message is one focusable element: "Capsule said: …" / "You said: …". Voice messages read as "Your voice note, 14 seconds. Transcript: …".
- Follow-up chips are a group with the question as its label; single-select groups behave as radios.
- New Capsule messages are announced politely; the user's own sent messages are not re-announced.
- At 200 % text the composer grows to 4 lines then scrolls; icon buttons keep their size.

### C2 Generating — accessibility
- Header status `chat.status.preparing` is a live region. Each completed step is announced once ("Checked budget: €89 of €100").
- Streaming text is **not** read token by token. The screen reader announces "Guide ready" when complete; the user then reads it normally.
- "Stop" is a labelled button (`a11y.stop`) ≥ 44 pt, reachable before the composer in focus order.

## F3 · Photo (clothes the user owns)

| Step | Screen | What happens | States |
| --- | --- | --- | --- |
| 1 | C1 | User taps camera. Action sheet: "Take a photo" / "Choose from library". | Offline: camera button disabled, label says `offline.media_disabled`. |
| 2 | P1 | First use only: reason sheet before the OS prompt (`perm.camera.*` or `perm.photos.*`). | Denied: `perm.*.denied` with "Open Settings"; the chat keeps working by text. |
| 3 | C1 | Preview with "Send" / "Retake". Device compresses to ≤ 1 MB and strips EXIF before upload. | Upload progress on the bubble. Too large / wrong type: `error.photo.invalid`. Upload failed: `error.photo.upload` + "Try again". |
| 4 | C1 | Header status `chat.status.reading_photo`. Capsule labels the clothes it found (tags on the photo) and lists them with "in the look" / "not used". | No clothes found: `error.photo.no_clothes`. Analysis failed: `error.photo.analysis`. |
| 5 | C1 | Capsule confirms which items it will reuse and shows `photo.privacy_note` under the reply. User can untick an item. | — |

Rules: Capsule names garments, colours and fit of the garment only. It never describes the person, their body or their looks, and never sets or changes the wardrobe from a photo. The local photo file is removed after upload succeeds (ADR-003).

### Accessibility
- Photo bubble label: "Your photo. Capsule found: dark straight jeans, brown leather boots." Tags on the image are also listed as text in the reply, so nothing is image-only.
- "Retake", "Send", and untick controls are labelled buttons / checkboxes.

## F4 · Voice

| Step | Screen | What happens | States |
| --- | --- | --- | --- |
| 1 | C1 | Tap mic to start, tap again to stop (no press-and-hold: easier for motor and screen-reader users). Max 60 s; a timer shows elapsed time. | Offline: mic disabled with `offline.media_disabled`. |
| 2 | P1 | First use only: `perm.mic.*` reason sheet before the OS prompt. | Denied: `perm.mic.denied` + "Open Settings"; the text field stays. |
| 3 | C1 | Recording: waveform, timer, "Stop", "Cancel". | Under 1 s: discarded silently with hint `voice.too_short`. 60 s reached: stops and sends. |
| 4 | C1 | Voice bubble sent; transcript appears under it (`voice.transcribing` → transcript). User can tap "Edit" on the transcript before Capsule answers. | Transcription failed: `error.voice.transcribe` with "Try again" and "Type instead". |

### Accessibility
- While recording, the screen reader announces "Recording" once and the timer every 15 s, not every second.
- Transcript is always shown as text (captions for the user's own audio, and needed for review).
- The play button on a voice bubble has `a11y.play_voice`.

## F5 · Guide (G1)

Layout follows `reference/02-guide.png` with the changes at the end of this file.

| Part | Content | Notes |
| --- | --- | --- |
| Header | Back, title "Your guide", share | Share exports text and links only, never the user's photo. |
| Wardrobe row | `guide.wardrobe_label` ("Menswear") + "Change" | "Change" starts F9. Replaces the Menswear/Womenswear toggle. |
| Summary | Occasion eyebrow, title, one-line why | — |
| Budget | `guide.budget.*`: total of budget, bar, "€11 left" | Numbers come from the budget validator in code, never from model text. |
| Sections | 1 Key pieces, 2 Base, 3 Details | Each item: image, name, price, one-line reason, "View at [shop]" or "From your photo". |
| Why this works | 2–3 bullets | Explains choices by occasion, colour, proportion of garments, never by body. |
| Feedback | 👍 / 👎 (`guide.feedback.*`) | Needed for helpful rate. 👎 opens optional chips: `guide.feedback.reasons` (too expensive, not my style, wrong for the occasion, something else). |
| Save | "Save guide" | Guest: opens A1 (F6). Signed in: saves to account. |

States:
- **Loading** (opened from a link or history before data arrives): skeleton of summary, budget and three items.
- **Product image missing:** neutral garment placeholder icon, not an empty box.
- **Product link unavailable / price changed:** item shows `guide.item.unavailable`; budget re-checks and shows the new total. If over budget, the item is marked and Capsule offers "Find an alternative".
- **No look fits the budget** (`error.guide.no_fit`): never shows an over-budget guide. Options: "Use more of my own clothes", "Show the key piece only", "Change budget".
- **Offline:** saved guides open fully from cache; "View at [shop]" is disabled with `offline.link_disabled`; feedback is queued.
- **Error loading:** `error.guide.load` + "Try again".

### Accessibility
- Heading levels: guide title H1, section titles H2, item names H3, so screen-reader users can jump by heading.
- Each item is one focus stop: "Unstructured blazer, navy, €48. Adds evening polish without the stiffness of a suit. Button: View at [shop], opens in browser."
- Budget bar has a text equivalent: "€89 of €100 spent, within budget, €11 left". The bar itself is decorative.
- "From your photo" is a text label, not only an icon.
- 👍 / 👎 have labels `a11y.helpful_yes` / `a11y.helpful_no` and expose selected state.
- At ≥ 150 % text, the price moves below the item name; the image shrinks to 56 pt before text is squeezed.

## F6 · Guest → sign-up (save moment)

The user gets the first guide as a guest. Sign-up is offered when it has a clear benefit: saving the guide, and later when they come back. It is never required to see or use a guide.

| Step | Screen | What happens | States |
| --- | --- | --- | --- |
| 1 | G1 | Guest taps "Save guide". | — |
| 2 | A1 | Bottom sheet: `save.sheet.*`. Primary: "Create account". Secondary: "Keep on this phone only". Close (X) = same as secondary. | Offline: sheet says an account needs a connection; only "Keep on this phone only" is enabled. |
| 3a | A2 | **Create account** → sign-up (E1). On success: every guest guide, chat and wardrobe/style/sizes choice on this phone moves to the account; toast `save.done_account`; user returns to G1 with "Saved". | Sign-up cancelled: back to A1. Sign-up failed: E1 error copy; guide is still saved on this phone. Email already registered: offer sign-in; after sign-in, guest guides are added to that account. |
| 3b | G1 | **Keep on this phone only** → guide saved locally, label "On this phone" on the guide and in L1. Toast `save.done_local`. | — |
| 4 | — | After a decline, later "Save" taps save locally without the sheet; G1 shows a small text link `save.inline_link`. The sheet is offered again at most once, on a later app open (F7 return banner). | — |

What a guest has:
- Guides and chats are kept on this phone (cache, ADR-003). They are lost if the app is deleted or the phone changes; A1 says so plainly.
- Analytics (if allowed) uses the same random id before and after sign-up, so the funnel stays continuous (needs an identify/alias step in E2).

Not in scope: sign-up methods and screens (E1); paywall or limits (the app is free).

### A1 — accessibility
- The sheet takes focus; the title is read first. Close button `a11y.close`. Both actions are full-width buttons ≥ 48 dp.
- Dismissible by swipe, the close button, and the Android back gesture; all three mean "Keep on this phone only".

## F7 · Saved guides (L1)

Reached from the header menu.

| State | What the user sees |
| --- | --- |
| Loading | Skeleton rows (3). Cached rows show at once; the list refreshes in place. |
| Empty | `saved.empty.*` + "Start a guide". |
| List | Rows: occasion title, date, "5 pieces · €89 of €100", badge "On this phone" for local-only guides. Newest first. |
| Return banner (guest with ≥ 1 local guide, second or later app open, shown once) | `saved.return_banner.*` with "Create account" and "Not now". |
| Offline | Banner; every saved guide opens from cache. Pull-to-refresh disabled with `offline.refresh_disabled`. |
| Error (refresh failed, online) | Inline `error.saved.refresh` above the cached list + "Try again". Never replaces cached content. |
| Delete | Swipe or "More" → "Delete guide" with confirm (`saved.delete.*`). Swipe is never the only way. |

### Accessibility
- Each row is one focus stop with the summary read in full and the badge included. Row actions are exposed as screen-reader custom actions ("Delete").
- The "More" button per row has label `a11y.more_guide`.

## F8 · Offline (C3)

Layout follows `reference/04-state-offline.png`.

| Situation | Behaviour |
| --- | --- |
| Going offline | Banner `offline.banner`; header subtitle unchanged. |
| Text message while offline | Queued on device, bubble in pending style with `offline.queued`. Sent in order when back online; then `chat.sent`. |
| Photo or voice while offline | Not queued. Camera and mic are disabled with `offline.media_disabled` (media are not kept on the device, ADR-003; transcription runs on the server). |
| Reply interrupted | Capsule bubble `error.connection_dropped` + "Try again". |
| Saved guides | Open fully (F7). Shop links disabled. |
| Composer placeholder | `chat.composer.placeholder_offline` |
| Back online | Banner disappears; announced as `offline.back_online`; queue sends. |
| Queued message older than 24 h | Stays queued but shows "Send now" / "Delete" so nothing is sent out of context without the user knowing. |

## F9 · Change wardrobe

Entry points: G1 "Change", chat header wardrobe label, Settings → Wardrobe.

| Step | What happens |
| --- | --- |
| 1 | Sheet with the three options, current one selected, plus `wardrobe.change.helper`. |
| 2a | From G1: choosing another option starts a **new** guide for the same request with the new wardrobe; the original guide stays as it was. Profile wardrobe is not changed unless the user ticks `wardrobe.change.make_default`. |
| 2b | From the chat header or Settings: the profile wardrobe changes and applies to the next guide. |
| Offline | Option list works; starting a new guide is queued as a text request (F8). |

Accessibility: options are a radio group; the sheet title states the context ("Wardrobe for this guide" vs "Your wardrobe").

## Analytics (proposed; to be agreed with product-analyst)

Nothing is sent before the user taps "Allow" on O2. If they choose "Not now", nothing is sent at all. Properties never include free text, sizes, budgets as typed, event descriptions, photos, transcripts or shop names. Ids are random and pseudonymous (ADR-004).

| Event | When | Properties |
| --- | --- | --- |
| `consent_given` | User taps "Allow" (on O2 or later in Settings) | `source`: onboarding \| settings |
| `onboarding_started` | O3 shown for the first time (first screen after the consent choice) | — |
| `onboarding_step_completed` | Leaving O3, O4 or O5 forward | `step`: wardrobe \| style \| sizes; `skipped`: bool |
| `onboarding_completed` | First C1 shown | `wardrobe`: menswear \| womenswear \| unisex \| skipped; `has_style`: bool; `has_sizes`: bool |
| `consultation_started` | First message of a consultation sent | `input`: text \| voice \| photo; `is_guest`: bool |
| `follow_up_answered` | User answers a follow-up | `via`: chip \| text \| voice |
| `permission_result` | OS permission dialog closes | `kind`: camera \| photos \| microphone; `granted`: bool |
| `guide_delivered` | Guide fully received and validated | `latency_ms` (send → complete); `within_budget`: bool; `owned_items_count`: int; `is_first`: bool; `is_guest`: bool |
| `guide_feedback` | 👍 / 👎 | `helpful`: bool; `reason`: too_expensive \| not_my_style \| wrong_for_event \| other \| none |
| `guide_saved` | Save completed | `destination`: account \| device |
| `signup_prompt_shown` | A1 or the return banner shown | `source`: save_sheet \| return_banner \| inline_link |
| `signup_completed` | Account created (fired by E1 flow) | `source`: save_sheet \| return_banner \| inline_link \| menu; `guest_guides_moved`: int |
| `message_queued_offline` | Text queued while offline | — |

`product_click` (click-through) belongs to E4 and is not redefined here.

### Activation denominator

Sign-up now comes after the first guide, so `guide_delivered / signup` no longer measures activation (most activated users would not have signed up yet, and some never will).

Proposal: **activation rate = users with `guide_delivered` (`is_first` = true) within 24 h of `onboarding_started` / users with `onboarding_started`.**

- `onboarding_started` is the earliest event any consenting user sends, so numerator and denominator come from the same consented group. Users who decline analytics are invisible to both sides; the rate is "activation among consenting users". This must be stated on dashboards.
- **Time to first guide** cannot start at "app open" (no event before consent). Proposal: `onboarding_started` → first `guide_delivered`, p95 < 90 s. It excludes O1/O2 time; a local, non-analytics timer could add it later if needed.
- Sign-up conversion becomes its own funnel: `guide_delivered (is_first)` → `signup_prompt_shown` → `signup_completed`.
- `docs/metrics.md` is updated by the Orchestrator, not in this card.

## Changes from the reference screens

| Reference | Change | Why |
| --- | --- | --- |
| `06-slide-2-photo.png` "Your photo is deleted after this step" | `photo.privacy_note`: "We only look at the clothes. Your photo is deleted once it's processed, and always within 24 hours." | ADR-008 guarantees deletion after processing and within 24 h, not instantly. |
| `02-guide.png` "Dark bottoms with a lighter top lengthen the silhouette" | "A lighter top over dark jeans keeps the look balanced and puts the focus on the blazer." | Comment on body shape; not allowed (root CLAUDE.md, blueprint §7). |
| `02-guide.png` Menswear/Womenswear toggle | Wardrobe label + "Change" (F9) | No Unisex option; switching a finished guide needs a new guide. Owner decision. |
| `01-chat.png`, `05-slide-1-ask.png` wardrobe asked in chat | Asked only if skipped in onboarding, once | The user already chose it; asking again adds a step to the first guide. |
| `01`/`03`/`04` "Stylist" with "S" avatar; `05` "Your stylist · online" | "Capsule", subtitle "AI stylist" or live status | One name; "online" and a person-like name suggest a human. Users must know they are talking to AI. |
| `07-slide-3-guide.png` "Checked by code" | `guide.budget.checked`: "Within budget · €11 left" | Developer wording. Precision of the check is shown by numbers, not by naming the mechanism. |
| `04-state-offline.png` (no media rule) | Photo and voice disabled offline, text queued | Media are not kept on the device (ADR-003); transcription runs on the server. |
| `02-guide.png` (no feedback) | 👍 / 👎 added | Needed for the helpful-rate metric. |

## Open questions

1. **Crash reports and consent** (security-engineer / owner): O2 covers usage analytics (PostHog). Whether Sentry crash reports (no PII, no screenshots) also need opt-in changes O2's copy and whether it has one switch or two. Copy is written for one switch covering usage analytics only.
2. **Guest session** (E1 / backend): a guest needs to call the API before sign-up. The mechanism (anonymous session, limits, how guest data on the server is linked at sign-up) is not a design decision, but F6 assumes guest guides can be moved to the account.
3. **Usability test** (blueprint §7): this spec should be tested with ≥ 5 people of different genders and ages before C1/G1 are built (E3). Results go into the E3 card.
