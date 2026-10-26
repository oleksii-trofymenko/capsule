# User flows (MVP)

Card: `docs/tasks/E0/E0-08-design-flows.md` · Metric: activation rate · Personas: [personas.md](personas.md) · Copy: [copy-deck.md](copy-deck.md) · Wireframes: [onboarding-wireframes.md](onboarding-wireframes.md) · Visual reference: [reference/](reference/).

Each step names its screen and its states. Copy is quoted by id from the copy deck. Accessibility notes sit under each screen; rules that apply everywhere are in "Global".

## Screen index

| Id | Screen | Source |
| --- | --- | --- |
| O1 | Welcome | Wireframe |
| O2 | Privacy choices (crash reports, usage events) | Wireframe |
| O3 | Wardrobe | Wireframe |
| O4 | Style | Wireframe |
| O5 | Sizes | Wireframe |
| C1 | Chat (ask, follow-up, photo, voice) | [01-chat.png](reference/01-chat.png), [05-slide-1-ask.png](reference/05-slide-1-ask.png), [06-slide-2-photo.png](reference/06-slide-2-photo.png) + wireframe for the first-run state |
| C2 | Chat, generating | [03-state-generating.png](reference/03-state-generating.png) |
| C3 | Chat, offline | [04-state-offline.png](reference/04-state-offline.png) |
| G1 | Guide | [02-guide.png](reference/02-guide.png), [07-slide-3-guide.png](reference/07-slide-3-guide.png), with the changes listed at the end |
| A1 | Save sheet (guest → sign-up) | Wireframe |
| A2 | Sign-up / sign-in | E1 card; this spec sets only entry, exit and the copy around it |
| L1 | Saved guides | Wireframe |
| P1 | Permission reason sheet (camera, photos, microphone) | Wireframe |
| W1 | Change wardrobe sheet | Wireframe |
| S1 | Settings → Privacy | Requirements below (F10); visual layout in E1/E3 |

## Global

These apply to every screen and are not repeated below.

- **Chat header:** title "Capsule". Subtitle shows a live status while Capsule works (`chat.status.thinking`, `chat.status.preparing`, `chat.status.reading_photo`); otherwise `chat.header.subtitle` ("AI stylist") or, when a wardrobe is set, `chat.header.subtitle_wardrobe` ("AI stylist · Menswear"). The title block is one button that opens W1, labelled `a11y.wardrobe_button`. Never "Stylist" alone, never "online": users must know they are talking to software.
- **Offline:** banner `offline.banner` at the top of content, announced once. Cached content stays usable; actions that need the network are disabled with a reason, not hidden.
- **Server unreachable** (online, but the API is down or times out): inline `error.server.title` + `error.server.body` + `error.try_again`. Never a blank screen or a raw error code.
- **Loading:** skeletons for content with a known shape (guide, saved list); a status line for work in progress (chat). No spinner-only state longer than 1 s.
- **Media on the device:** a photo is shown only until its upload succeeds; then the bubble shows a neutral photo icon and the garments found, as text. Voice bubbles show duration and transcript only (no playback). No photo, thumbnail, audio or media URL is written to MMKV or the query cache. The device compresses photos to ≤ 1 MB and strips EXIF; the server strips EXIF again (ADR-003, ADR-008).
- **No inference:** Capsule never infers gender, age or any other personal trait from a photo, a voice, a name or a size, and never sets the wardrobe from them.
- **Accessibility:**
  - Every icon button has a label (`a11y.*`) and a 44 pt / 48 dp target, even when the icon is 24 pt. Header icons: `a11y.menu`, `a11y.new_chat`, `a11y.back`, `a11y.share`, `a11y.close`.
  - Dynamic Type / font scale up to 200 %: text wraps, headings and prices never truncate; chip groups wrap; side-by-side rows (name + price, budget label + amount) stack above 150 %.
  - Reduce Motion: typing dots, streaming caret and step spinners become static; status is still announced.
  - Focus order follows reading order: header, content top to bottom, then composer or primary button.
  - Status changes (offline, queued, sent, guide ready) are polite live-region announcements, not alerts.
  - Selected chips and rows expose a "selected" state, not only colour; the tick icon is decorative.
  - Contrast is verified against WCAG AA when tokens land (E0-09), including white text on both ends of the brand gradient and muted text on the lightest background.

## F1 · Onboarding (first launch)

Goal: reach the first ask in **6 taps** when every optional step is skipped (Get started → a privacy choice → a wardrobe → Continue → Skip → Skip). No auto-advance: moving on without a tap confuses screen-reader and switch users. Style and sizes are optional so time to first guide stays under 90 s (p95). Nothing here creates an account: the user continues as a guest (F6).

| Step | Screen | What happens | States |
| --- | --- | --- | --- |
| 1 | O1 Welcome | `onb.welcome.title`, `onb.welcome.body`, `onb.welcome.cta`, `onb.welcome.legal`. | Offline: `offline.welcome` under the body; "Get started" still works. |
| 2 | O2 Privacy choices | Two switches, both **off** by default: crash reports (Sentry) and usage events (PostHog). `onb.consent.allow` turns both on and continues; `onb.consent.decline` keeps both off and continues; once any switch is on, the second button becomes `onb.consent.save`. Neither SDK is initialised before a choice. | Either choice continues. Choice stored on the device; changeable in S1. |
| 3 | O3 Wardrobe | Menswear, Womenswear, Unisex (single select) or `onb.skip`. | Nothing selected: `onb.continue` disabled, `onb.skip` always enabled. |
| 4 | O4 Style | Up to 3 style chips. `onb.continue` works with none selected. | Optional; `onb.skip` continues. |
| 5 | O5 Sizes | Tops, bottoms, shoes; size system EU / UK / US. | Optional; partial entry is fine. |
| 6 | C1 Chat, first run | `chat.empty.greeting` and three example prompts covering menswear, womenswear and unisex occasions. | See F2. |

Back (`a11y.back`) on O3–O5 keeps choices. Killing the app mid-onboarding resumes at the last unfinished step.

### O1 Welcome — accessibility
- The heading is the first focus. Any illustration is decorative, hidden from the screen reader, and shows no people.

### O2 Privacy choices — accessibility
- Each switch row is one focus stop: label, description, state ("Crash reports, off, switch").
- Both buttons have the **same size and the same visual style**, stacked, full width, ≥ 48 dp. No pre-selected choice, no grey "dark-pattern" link.
- `onb.consent.details_toggle` is a real button that expands `onb.consent.details` inline.

### O3 Wardrobe — accessibility
- Options are a radio group, each a full-width row ≥ 56 pt with label and one-line description. `onb.wardrobe.helper` is read after the title, before the options.

### O4 Style — accessibility
- Chips are checkboxes. After each change the screen reader says `a11y.style_count`. With 3 chosen, other chips are announced as `a11y.style_max` and `onb.style.max` is shown as text.

### O5 Sizes — accessibility
- Each size is a labelled picker (`a11y.size_picker`). No free-text size fields. The size system is a segmented control with three labelled segments.
- Copy speaks about sizes "you usually buy", never about bodies.

## F2 · Ask → follow-up → guide

| Step | Screen | What happens | States |
| --- | --- | --- | --- |
| 1 | C1 | User describes occasion and budget by text, voice (F4) or photo (F3). Example prompts (`chat.empty.examples_label`, `chat.empty.example_1`, `chat.empty.example_2`, `chat.empty.example_3`) fill the composer; they do not send. | First run: greeting + examples. Composer empty: send disabled, mic enabled. Placeholder `chat.composer.placeholder`. Offline: text is queued (F8). |
| 2 | C1 | Capsule asks only what it still needs, as chips plus free reply (`chat.followup.intro`, `chat.followup.voice_hint`). If the wardrobe was set in onboarding it is **not** asked again. If it was skipped, Capsule asks once (`chat.followup.wardrobe`) and saves the answer to the profile. | Typing indicator with `chat.status.thinking`. Error: `error.server.title` + `error.try_again` on the failed message. |
| 3 | C2 | Generating: progress steps, then the guide streams in. `chat.stop` is available. Composer stays active (`chat.composer.placeholder_busy`). | Stopped: partial guide discarded, `chat.stopped` + `error.try_again`. Timeout > 60 s: `error.guide.timeout`. No look fits: `error.guide.no_fit` with `error.guide.no_fit.own`, `error.guide.no_fit.key_only`, `error.guide.no_fit.budget`. |
| 4 | G1 | Guide card in chat; tap opens the full guide. | See F5. |

C2 progress steps, in order (each shown only if it applies):

| Step | Copy id | Source of the values |
| --- | --- | --- |
| Request understood | `guide.progress.understood` | Parsed request (occasion, budget, constraints) |
| Photo analysed | `guide.progress.photo` | Garment names from the vision step |
| Pieces found | `guide.progress.found` / `guide.progress.found_one` | Count from the product search |
| Budget checked | `guide.progress.budget` | Budget validator in code, never model text |
| Writing | `guide.progress.writing` | — |
| Done (announcement only) | `a11y.guide_ready` | — |

### C1 Chat — accessibility
- Composer order: camera (`a11y.camera`), text field, microphone (`a11y.mic`), send (`a11y.send`).
- Each message is one focus stop: `a11y.msg_capsule` / `a11y.msg_user`; voice messages `a11y.msg_voice`; photos `a11y.msg_photo`.
- Follow-up chips are a group labelled by their question; single-select groups behave as radios.
- New Capsule messages are announced politely; the user's own sent messages are not re-announced.
- At 200 % text the composer grows to 4 lines then scrolls; icon buttons keep their size.

### C2 Generating — accessibility
- The header status is a live region. Each completed step is announced once, using the step's copy.
- Streaming text is **not** read token by token. When complete, `a11y.guide_ready` is announced; the user then reads the guide normally.
- `chat.stop` is a labelled button (`a11y.stop`) ≥ 44 pt, before the composer in focus order.

## F3 · Photo (clothes the user owns)

| Step | Screen | What happens | States |
| --- | --- | --- | --- |
| 1 | C1 | User taps camera. Action sheet: `photo.source.camera` / `photo.source.library`. | Offline: camera disabled, reason `offline.media_disabled`. |
| 2 | P1 | First use only: reason sheet before the OS prompt (`perm.camera.title`/`perm.camera.body` or `perm.photos.title`/`perm.photos.body`, buttons `perm.continue` / `perm.not_now`). | Denied: `perm.camera.denied` or `perm.photos.denied` + `perm.open_settings`; chat keeps working by text. |
| 3 | C1 | Preview with `photo.preview.send` / `photo.preview.retake`. Compression to ≤ 1 MB and EXIF removal on the device before upload. | Upload progress on the bubble. Wrong type: `error.photo.invalid`. Upload failed: `error.photo.upload` + `error.try_again`. |
| 4 | C1 | Upload succeeds: the local photo is removed and the bubble becomes a neutral photo icon. Header `chat.status.reading_photo`. Capsule lists the garments it found as text, each marked `photo.item.in_look` or `photo.item.not_used`. | No clothes found: `error.photo.no_clothes`. Analysis failed: `error.photo.analysis`. |
| 5 | C1 | Capsule confirms which items it will reuse; `photo.privacy_note` under the reply. The user can untick an item. | — |

Rules: Capsule names garments, colours and fit of the garment only. It never describes the person, their body or looks, and never infers gender, age or any other trait from a photo.

### Accessibility
- Photo bubble: `a11y.msg_photo`. Found garments are text in the reply, so nothing is image-only.
- Retake, Send and the untick controls are labelled buttons / checkboxes.

## F4 · Voice

| Step | Screen | What happens | States |
| --- | --- | --- | --- |
| 1 | C1 | Tap mic to start, tap again (`a11y.mic_stop`) to stop. No press-and-hold (easier for motor and screen-reader users). Limit `voice.limit` (60 s), elapsed timer shown. | Offline: mic disabled, reason `offline.media_disabled`. |
| 2 | P1 | First use only: `perm.mic.title` / `perm.mic.body` before the OS prompt. | Denied: `perm.mic.denied` + `perm.open_settings`; the text field stays. |
| 3 | C1 | Recording: `voice.recording`, waveform, timer, stop, `voice.cancel`. | Under 1 s: discarded; shows `voice.too_short`. 60 s reached: stops and sends. |
| 4 | C1 | Voice bubble shows duration; `voice.transcribing` then the transcript under `voice.transcript_label`. The user can tap `voice.edit` before Capsule answers. The local recording is removed after upload. | Transcription failed: `error.voice.transcribe` + `error.try_again` + `error.voice.type_instead`. |

Rules: Capsule uses only the words. It never infers gender, age, accent, mood or any other trait from a voice.

### Accessibility
- While recording, the screen reader announces `a11y.recording` once and `a11y.recording_elapsed` every 15 s, not every second.
- The transcript is always shown as text.

## F5 · Guide (G1)

Layout follows [02-guide.png](reference/02-guide.png) with the changes at the end of this file.

| Part | Content | Notes |
| --- | --- | --- |
| Header | Back, `guide.title`, share (`a11y.share`) | Share exports text and links only, never a photo. |
| Wardrobe row | `guide.wardrobe_label` + `guide.wardrobe_change` | Opens W1 for this guide. Replaces the Menswear/Womenswear toggle. |
| Summary | Occasion eyebrow, title, one-line why | — |
| Budget | `guide.budget.label`, `guide.budget.amount`, bar, `guide.budget.checked` or `guide.budget.over` | Numbers come from the budget validator in code, never from model text. "Within budget" is shown only when it is true. |
| Sections | `guide.section.key` + `guide.section.key.sub`, `guide.section.base` + `guide.section.base.sub`, `guide.section.details` + `guide.section.details.sub` | Item: image, name, price, one-line reason, `guide.item.view` or `guide.item.owned`. |
| Why this works | `guide.why.title`, 2–3 bullets | Explains by occasion, colour and the proportions of garments, never by body. |
| Feedback | `guide.feedback.question`, 👍 / 👎, `guide.feedback.thanks` | 👎 opens optional chips `guide.feedback.reason_title` / `guide.feedback.reasons`. |
| Save | `guide.save` → `guide.saved` | Guest: opens A1 (F6). Signed in: saves to the account. |

States:
- **Loading** (opened from history before data arrives): skeleton of summary, budget and three items.
- **Product image missing:** neutral garment icon, not an empty box.
- **Product unavailable or price changed:** item shows `guide.item.unavailable` and `guide.item.find_alternative`; the budget is re-checked by code. If the new total is over budget, the budget row shows `guide.budget.over` (bar full, with an "over" text label, not colour alone) and the screen reader reads `a11y.budget_summary_over`.
- **No look fits the budget:** never shows an over-budget guide; see F2 step 3.
- **Offline:** saved guides open fully; `guide.item.view` is disabled with `offline.link_disabled`; feedback is queued.
- **Error loading:** `error.guide.load` + `error.try_again`.

### Accessibility
- Heading levels: guide title H1, section titles H2, item names H3.
- Each item is one focus stop: name, price, reason, then the link (`a11y.item_link`).
- Budget bar is decorative; its text equivalent is `a11y.budget_summary` or `a11y.budget_summary_over`.
- `guide.item.owned` is a text label, not only an icon.
- 👍 / 👎: `a11y.helpful_yes` / `a11y.helpful_no`, exposing the selected state.
- At ≥ 150 % text the price moves below the item name; the image shrinks to 56 pt before text is squeezed.

## F6 · Guest → sign-up (save moment)

The first guide needs no account. Sign-up is offered when it has a clear benefit: saving a guide, and once on a later visit. It is never required to see or use a guide.

| Step | Screen | What happens | States |
| --- | --- | --- | --- |
| 1 | G1 | Guest taps `guide.save`. | — |
| 2 | A1 | Bottom sheet: `save.sheet.title`, `save.sheet.body`, `save.sheet.create`, `save.sheet.local`, `save.sheet.local_warning`. Close (`a11y.close`) = `save.sheet.local`. | Offline: `save.sheet.offline` replaces the body; only `save.sheet.local` is enabled. |
| 3a | A2 | **Create account** → sign-up (E1). On success the guest data moves to the account (see "Guest data"); toast `save.done_account`; back to G1 showing `guide.saved`. | Cancelled: back to A1. Failed: E1 error copy; the guide is still saved on this phone. Email already registered: offer sign-in; after sign-in the guest data moves to that account. |
| 3b | G1 | **Save on this phone** → saved locally, badge `guide.on_device` on the guide and in L1; toast `save.done_local`. | — |
| 4 | — | After a decline, later saves happen locally without the sheet; G1 shows the text link `save.inline_link`. | — |

**Return banner — one trigger:** shown at the top of L1 the first time L1 is opened at least 24 h after the guest's first local save. Shown once, guests only; either button dismisses it for good.

### Guest data (requirements for E1)

Design depends on these; E1 owns how they are built.

- The guest credential lives only in `expo-secure-store` (ADR-003), like account tokens.
- The server holds only what a consultation needs (requests, voice transcripts, garments found in photos, follow-up answers, guides, wardrobe/style/sizes choices). Media follow ADR-008. Retention, deletion, export and moving to an account cover all of these.
- Guest data on the server is deleted N days after the last activity. N is in config; the upper bound is fixed in an E1 ADR (30 days proposed) and stated in the Privacy notice (`save.sheet.local_warning` uses `{retention_days}`).
- "Delete my data" is available to guests and account holders (F10). It deletes server data, the PostHog person, Sentry data for the id, and both local stores (secure-store and MMKV, including saved guides). E2 note: Sentry per-id deletion on the free plan must be verified; if it is not possible, propose an ADR-004 amendment (crash reports carry no user or guest id and expire with Sentry retention) and change `privacy.delete.body_guest` / `privacy.delete.body_account` accordingly. The current text stays until then.
- Data export is available on the same terms as deletion.
- Moving guest data to an account happens only during sign-up or sign-in, in one step that presents the guest credential and the new token together; the guest credential is then revoked. Guest data is never matched by email, device or analytics id.
- Rate limits apply per guest credential and per IP.
- The analytics alias (guest id → account) happens only if usage events are allowed.

### Saved guides on this phone (requirements for E3/E7)

- Stored under their own MMKV key via `apps/mobile/shared/storage`, separate from the query cache: never evicted, expired or cleared by the query-cache persister or by app updates.
- Excluded from OS backups; text and product data only (no photos, thumbnails or media URLs).
- Wiped by logout, account deletion, "Delete my data" and the first launch after reinstall (ADR-003).

### A1 — accessibility
- The sheet takes focus and its title is read first. Both actions are full-width buttons ≥ 48 dp.
- Swipe down, the close button and Android back all mean `save.sheet.local`.

## F7 · Saved guides (L1)

Reached from the header menu. Title `saved.title`.

| State | What the user sees |
| --- | --- |
| Loading | Three skeleton rows. Cached rows show at once and refresh in place. |
| Empty | `saved.empty.title`, `saved.empty.body`, `saved.empty.cta`. |
| List | Row: occasion title, date, `saved.row.summary`, badge `guide.on_device` for local-only guides. Newest first. |
| Return banner | `saved.return_banner.title`, `saved.return_banner.body`, `saved.return_banner.create`, `saved.return_banner.dismiss`. Trigger in F6. |
| Offline | Banner; every saved guide opens from the phone. Pull-to-refresh disabled with `offline.refresh_disabled`. |
| Error (refresh failed, online) | `error.saved.refresh` above the cached list + `error.try_again`. Never replaces cached content. |
| Delete | Swipe or "More" (`a11y.more_guide`) → `saved.delete.action` → confirm `saved.delete.title` with `saved.delete.body` (phone-only guide) or `saved.delete.body_account` (account guide), buttons `saved.delete.confirm` / `saved.delete.cancel`. Swipe is never the only way. |

### Accessibility
- Each row is one focus stop with the summary and badge read in full; row actions are exposed as screen-reader custom actions.

## F8 · Offline (C3)

Layout follows [04-state-offline.png](reference/04-state-offline.png).

| Situation | Behaviour |
| --- | --- |
| Going offline | Banner `offline.banner`. |
| Text message while offline | Queued on the device; pending bubble with `offline.queued`. Sent in order when back online, then `chat.sent`. |
| Photo or voice while offline | Not queued. Camera and mic disabled with `offline.media_disabled` (media are not kept on the device; transcription runs on the server). |
| Reply interrupted | Capsule bubble `error.connection_dropped` + `error.try_again`. |
| Saved guides | Open fully (F7). Shop links disabled. |
| Composer placeholder | `chat.composer.placeholder_offline` |
| Back online | Banner disappears; `offline.back_online` announced; queue sends. |
| Queued message older than 24 h | Not sent automatically: `offline.queued_old` with `offline.queued_send` / `offline.queued_delete`. |

## F9 · Change wardrobe (W1)

Entry points: G1 `guide.wardrobe_change`, the chat header button, Settings.

| Step | What happens |
| --- | --- |
| 1 | Sheet with Menswear, Womenswear, Unisex (`onb.wardrobe.men` / `.women` / `.unisex`); the current one is selected and marked `wardrobe.change.current`. `wardrobe.change.cancel` closes it. |
| 2a | From G1: title `wardrobe.change.title_guide`, helper `wardrobe.change.helper`, button `wardrobe.change.cta_guide`. Starts a **new** guide for the same request; the original stays as it was. The profile changes only if the user ticks `wardrobe.change.make_default`. |
| 2b | From the chat header or Settings: title `wardrobe.change.title_profile`, helper `wardrobe.change.helper_profile`, button `wardrobe.change.cta_profile`. Applies to the next guide. |
| Offline | The sheet works; a new guide is queued as a text request (F8). |

Accessibility: the options are a radio group; the sheet title states the context.

## F10 · Settings → Privacy (S1)

Requirements only; layout in E1/E3.

- The two switches from O2 (`onb.consent.crash.label`, `onb.consent.usage.label`, with their descriptions). Turning one off stops that SDK at once, deletes its queued data and resets its id. No "withdrawn" event is sent.
- `privacy.export` — download my data (guest or account).
- `privacy.delete` → confirm `privacy.delete.title` with `privacy.delete.body_guest` or `privacy.delete.body_account`, buttons `privacy.delete.confirm` / `saved.delete.cancel`. Needs a connection. The server deletion runs first; the local stores (including the guest credential) are wiped only after the server confirms, then `privacy.delete.done` is shown. If it fails, nothing local is wiped and `error.server.title` + `error.try_again` is shown. Offline: `privacy.delete.offline`, button disabled.

## Analytics (agreed with product-analyst, 2026-10-26)

Usage events are sent only while the "Usage events" switch is on (O2 / S1). Properties never include free text, sizes, budget amounts, occasion details, photos, transcripts or shop names. Metric definitions: [`docs/metrics.md`](../metrics.md) → Definitions.

| Event | When | Properties |
| --- | --- | --- |
| `consent_given` | Usage events switched on | `source`: onboarding \| settings |
| `app_opened` | Cold start, or foreground after ≥ 30 min in the background | `is_guest` |
| `onboarding_started` | O3 first shown. Once per install; never back-filled if usage events are turned on later | — |
| `onboarding_step_completed` | Leaving O3, O4 or O5 forwards. May repeat if the user goes back | `step`: wardrobe \| style \| sizes; `skipped` (true only for "Skip for now") |
| `onboarding_completed` | First C1 shown | `wardrobe`: menswear \| womenswear \| unisex \| skipped; `has_style`; `has_sizes` |
| `consultation_started` | First message of a consultation sent | `input`: text \| voice \| photo; `is_guest`; `from_example` |
| `follow_up_answered` | User answers a follow-up | `via`: chip \| text \| voice |
| `permission_result` | OS permission dialog closes | `kind`: camera \| photos \| microphone; `granted` |
| `guide_delivered` | Guide fully received and validated | `guide_id`; `latency_ms` (user's last message before generation → guide complete); `within_budget`; `owned_items_count`; `follow_ups_count`; `is_first` (first guide ever on this install; the device sets it whether or not usage events are on); `is_guest`; `since_onboarding_ms` (only when `is_first`) |
| `guide_failed` | A consultation ends without a guide | `reason`: timeout \| no_fit \| server_error \| connection_dropped \| stopped_by_user; `is_guest` |
| `guide_feedback` | 👍 / 👎 tapped | `guide_id`; `helpful` |
| `guide_feedback_reason` | A 👎 reason chip tapped | `guide_id`; `reason`: too_expensive \| not_my_style \| wrong_for_occasion \| other |
| `guide_saved` | Save completed | `guide_id`; `destination`: account \| device |
| `wardrobe_changed` | Wardrobe changed after onboarding | `source`: guide \| chat_header \| settings \| chat_followup; `new_guide` |
| `signup_prompt_shown` | A1 or the return banner shown | `source`: save_sheet \| return_banner |
| `signup_started` | A2 opened | `source`: save_sheet \| return_banner \| inline_link \| menu |
| `signup_completed` | Account created (E1 flow) | `source`: save_sheet \| return_banner \| inline_link \| menu; `guest_guides_moved` |
| `message_queued_offline` | Text queued while offline | — |

Rules:
- `guide_id` is a random UUID issued by the server, never a user id. E4's `product_click` carries it.
- Events raised offline are queued with the time of the tap and sent later.
- Turning usage events off stops sending at once and resets the analytics id. No withdrawal event.
- Identity (E2): sign-up keeps the same distinct id. Signing in on another device identifies with a random analytics id stored on the account, never the account id, email or a hash of either.

### Activation and time to first guide

Defined in [`docs/metrics.md`](../metrics.md) → Definitions. In short:
- **Activation:** users whose first `guide_delivered` (`is_first` = true) arrives within 24 h of `onboarding_started` ÷ users with `onboarding_started`. Only users with usage events on are counted.
- **Time to first guide:** `since_onboarding_ms` on the first `guide_delivered`; p50 and p95 over activated users; target p95 < 90 s. It excludes O1 and O2 (nothing may be sent before the choice) and includes background time.

## Changes from the reference screens

| Reference | Change | Why |
| --- | --- | --- |
| [06-slide-2-photo.png](reference/06-slide-2-photo.png) "Your photo is deleted after this step" | `photo.privacy_note` | ADR-008 guarantees deletion after processing and within 24 h, not instantly. |
| [06-slide-2-photo.png](reference/06-slide-2-photo.png) tags drawn on the photo | Photo replaced by a neutral icon after upload; garments listed as text | Media are not kept on the device after upload (ADR-003); analysis happens after upload. |
| [01-chat.png](reference/01-chat.png), [05-slide-1-ask.png](reference/05-slide-1-ask.png) voice bubble with play button | Duration + transcript, no playback | The recording is not kept on the device. |
| [02-guide.png](reference/02-guide.png) "Dark bottoms with a lighter top lengthen the silhouette" | "A lighter top over dark jeans keeps the look balanced and puts the focus on the blazer." | Comment on body shape (root CLAUDE.md, blueprint §7). |
| [02-guide.png](reference/02-guide.png) Menswear/Womenswear toggle | `guide.wardrobe_label` + `guide.wardrobe_change` (F9) | No Unisex option; switching a finished guide needs a new guide. Owner decision. |
| [01-chat.png](reference/01-chat.png), [05-slide-1-ask.png](reference/05-slide-1-ask.png) wardrobe asked in chat | Asked only if skipped in onboarding, once | The user already chose it. |
| [01-chat.png](reference/01-chat.png) "so the guide fits you" | `chat.followup.intro` | Keeps the focus on the occasion, not the person. |
| [01-chat.png](reference/01-chat.png) / [03](reference/03-state-generating.png) / [04](reference/04-state-offline.png) "Stylist", "S" avatar; [05](reference/05-slide-1-ask.png) "Your stylist · online" | "Capsule", `chat.header.subtitle` | One name; "online" and a person-like name suggest a human. |
| [07-slide-3-guide.png](reference/07-slide-3-guide.png) "Checked by code" | `guide.budget.checked` | Developer wording. |
| [04-state-offline.png](reference/04-state-offline.png) (no media rule) | Photo and voice disabled offline; text queued | Media are not kept on the device; transcription runs on the server. |
| [02-guide.png](reference/02-guide.png) (no feedback) | 👍 / 👎 added | Needed for the helpful-rate metric. |

## Open questions

1. ~~Crash reports and consent~~ — **resolved:** O2 has two switches, both off by default. Crash-free and app-start metrics therefore cover only users who allow crash reports.
2. ~~Guest session~~ — **resolved at spec level:** see "Guest data (requirements for E1)". E1 owns the mechanism and the retention ADR.
3. **Durable local storage for saved guides** (E1/E3): phone-only saved guides must survive cache eviction and app updates. ADR-003 keeps MMKV and defers SQLite; E3 must confirm a separate MMKV key is enough or propose an ADR.
4. **Usability test** (blueprint §7): test with ≥ 5 people of different genders and ages before C1/G1 are built (E3); results go into the E3 card.
