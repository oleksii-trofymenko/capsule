# Base components

Card: `docs/tasks/E0/E0-09-design-tokens.md` · Tokens: [tokens.json](tokens.json) · Screens and states: [flows.md](flows.md) · Copy: [copy-deck.md](copy-deck.md) · Visual reference: [reference/](reference/).

This file sets how each shared component looks and behaves in every state. Screens in `flows.md` are built only from these components. Text is quoted by copy id, never written here. Values are token paths from `tokens.json`. The mobile UI kit (`apps/mobile/shared/`) builds each component once, with the same name.

## How to read

- `text.primary` means `semantic.<scheme>.text.primary` (import: `theme[scheme].text.primary`). `base.*` tokens are the same in both themes (`base.space.4` = 16).
- Sizes are minimums. Every component grows with the user's text size. Fixed heights are never used.
- "Hit 48" means the touch area is at least 48 × 48 (`base.size.touchTarget`). If the visual is smaller, add `hitSlop`.

## Rules for every component

1. **Font.** Plus Jakarta Sans, weights 400–800, bundled with the app (E1). There is no system-font fallback except while fonts load, and the splash screen stays up until then.
2. **Text size.** Font scaling is always on, with `maxFontSizeMultiplier` = `base.font.scale.max` (2). From a font scale of 1.5 up, side-by-side pairs (name + price, label + amount) stack, and item images shrink to `base.size.itemImageCompact`. Headings and prices wrap, never truncate.
3. **States.** Every interactive component defines **default, pressed, disabled and focus**. Some also have selected, loading or error states, listed under the component.
   - **Pressed:** white surfaces turn `surface.pressed`. The brand gradient gets the `surface.pressedOnBrand` overlay; it is never lightened, because lightening drops white text below 4.5:1. Duration `base.motion.duration.fast`.
   - **Disabled:** `surface.disabled` + `text.disabled`, with no opacity fade. Text stays at 4.5:1 or more so the user can still read what is unavailable. The reason is shown as text next to the control (for example `offline.media_disabled`), and the screen reader says "dimmed" / "disabled" plus the reason as a hint.
   - **Focus** (keyboard, switch control, Android D-pad): a ring `base.size.focusRingWidth` thick in `focus.ring`, offset by `base.size.focusRingOffset`, following the component's radius. The screen-reader cursor is drawn by the OS and is not restyled.
4. **Status never relies on colour alone.** Each status has an icon **and** words: within/over budget, queued, sent, failed, offline, on device, selected. Warning and error share the `rust` hue and success uses `plum`, so there is no red/green pair (Tomasz). Status icons are decorative to screen readers because the words carry the meaning.
5. **Selected state** is shown by a tick icon + gradient fill + `accessibilityState.selected` / `checked`, never by fill alone.
6. **Reduce Motion:** durations become 0. Typing dots, spinner and streaming caret are static. Status is still announced.
7. **Dark theme** follows the system setting. Every component uses semantic tokens only, so dark needs no separate spec. Exceptions are noted under the component.
8. **Shadows instead of borders** for surfaces (`shadow.md`), per the visual direction. Borders are used only where a control needs a 3:1 edge (`border.control`).

## 1. Button

| Variant | Use | Surface | Label | Size | Radius | Shadow |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | One main action per view: `onb.welcome.cta`, `onb.continue`, `error.try_again`, `save.sheet.create`, `wardrobe.change.cta_*` | `gradient.brand` | `textStyle.label`, `text.onBrand`; optional 16 leading icon `icon.onBrand` | height ≥ `size.buttonHeight`, padding x `space.5` | `pill` | `shadow.brand` |
| Secondary | Equal-weight alternatives: `onb.consent.allow` and `onb.consent.decline` (both use this style, same size: no nudging), `save.sheet.local`, `perm.not_now`, `saved.delete.cancel`, `chat.stop` | `surface.card` + 1 px `border.control` | `textStyle.label`, `text.primary` | as primary | `pill` | `shadow.sm` |
| Link button | Item actions: `guide.item.view`, `guide.item.find_alternative`, `perm.open_settings`, `error.voice.type_instead` | `surface.card` + 1 px `border.control` | `textStyle.labelSmall`, `text.link`; trailing "opens outside" icon 16 for shop links | height ≥ `size.linkButtonHeight`, padding x `space.3` | `md` | none |
| Text link | Inline, low emphasis: `onb.consent.details_toggle`, `save.inline_link`, `guide.wardrobe_change` | none | `textStyle.labelSmall`, `text.link`, underlined | hit 48 | — | — |
| Destructive | Confirms deletion: `saved.delete.confirm`, `privacy.delete.confirm`, `offline.queued_delete` | `surface.card` + 1 px `border.control` | `textStyle.label`, `text.accent` + leading trash icon `icon.accent` | as primary | `pill` | `shadow.sm` |

On O2, `onb.consent.allow`, `onb.consent.decline` and `onb.consent.save` are all **Secondary** and full width, stacked. A gradient would pre-select a choice (flows.md O2). The destructive button is never the gradient. Its icon and copy say "delete"; colour does not.

| State | Primary | Secondary / Link / Destructive | Text link |
| --- | --- | --- | --- |
| Default | as above | as above | as above |
| Pressed | `surface.pressedOnBrand` overlay; shadow drops to none | `surface.pressed`; link label `text.linkPressed` | `text.linkPressed` |
| Disabled | `surface.disabled`, label `text.disabled`, no shadow | `surface.disabled`, no border, label `text.disabled` | `text.disabled`, no underline |
| Focus | ring `focus.ring` around the pill | same | ring around the text bounds |
| Loading | label replaced by a 16 spinner (`control.progressFill` on white for primary) + the same label read to the screen reader with "busy"; width does not change; not pressable | same | — |

Accessibility: role `button`; the label is the visible text. A link button that leaves the app uses `a11y.item_link`.

### Icon button

Header (`a11y.menu`, `a11y.new_chat`, `a11y.back`, `a11y.share`, `a11y.close`) and composer (`a11y.camera`, `a11y.mic`, `a11y.mic_stop`, `a11y.send`).

| Part | Value |
| --- | --- |
| Size | `size.iconButton` (48) hit and visual; icon `size.icon` (24) in `icon.default` |
| Send variant | visual `size.sendButton` (44) circle, `gradient.brand`, `shadow.brand`, arrow `icon.onBrand`; hit 48 |
| Pressed | circle `surface.pressed` behind the icon; send gets `surface.pressedOnBrand` |
| Disabled | icon `icon.muted`; send becomes `surface.disabled` with the arrow in `text.disabled`; hint gives the reason |
| Focus | ring around the 48 circle |
| Label | always set from the `a11y.*` id; never "button" or the icon name |

The icon keeps its size at every text scale; the hit area never shrinks.

## 2. Chip

| Variant | Use | Behaviour |
| --- | --- | --- |
| Choice | Follow-up questions (C1), `onb.wardrobe.*` inside chat (`chat.followup.wardrobe`) | Single select in a group = radio |
| Multi | O4 style chips (`onb.style.options`), max 3 | Checkbox; after 3, the rest are disabled with `a11y.style_max` and `onb.style.max` shown as text |
| Suggestion | `chat.empty.example_1..3` | Button; fills the composer, does not send |
| Feedback reason | `guide.feedback.reasons` after the thumbs-down | Single select, optional |

| Part | Value |
| --- | --- |
| Shape | height ≥ `size.chipHeight` (44), hit 48, padding x `space.4`, radius `pill`, gap between chips `space.2`; groups wrap |
| Label | `textStyle.labelSmall` |
| Unselected | `surface.card`, 1 px `border.control`, label `text.primary`, `shadow.sm` |
| Selected | `gradient.brand`, no border, label `text.onBrand`, leading tick 16 `icon.onBrand`, `shadow.brand` |
| Suggestion | `surface.card`, `border.control`, label `text.primary`, leading 16 "speech" icon `icon.brand`; never selected |
| Pressed | unselected: `surface.pressed`; selected: `surface.pressedOnBrand` |
| Disabled | `surface.disabled`, no border, label `text.disabled` |
| Focus | ring around the pill |

Accessibility: the group is labelled by its question (for example `chat.followup.wardrobe`). Each chip has role `radio` or `checkbox` with a selected/checked state. The tick is decorative.

## 3. Message bubble (with tail)

| Part | Capsule | User |
| --- | --- | --- |
| Alignment | left; max width `size.bubbleMaxWidth` of content | right; same max width |
| Surface | `surface.card` | `gradient.brand` |
| Text | `textStyle.body`, `text.primary` | `textStyle.bodyMedium`, `text.onBrand` |
| Padding | `space.3` vertical, `space.4` horizontal | same |
| Radius | `xl` on three corners, `xs` bottom-left | `xl` on three corners, `xs` bottom-right |
| Tail | `size.tailWidth` × `size.tailHeight` curve at the bottom-left corner, sticking out 7 to the left, filled `surface.card` | mirrored at the bottom-right, filled with the gradient end colour (`primitive.color.plum.500` via `gradient.brand` last stop) |
| Shadow | `shadow.md` | `shadow.brand` |
| Gap | `space.3` between consecutive bubbles, `space.4` when the speaker changes | same |

Tail shape (from the canvas): path `M0 0 C0 9 4 15 14 18 H0 Z` in a 14 × 18 box, aligned to the bubble's bottom edge. Only the last bubble of a run from the same speaker has a tail. There is no avatar; the header names Capsule (flows.md Global).

Variants and states:

| Variant / state | Spec | Copy |
| --- | --- | --- |
| Sent | user bubble; status line under it, right-aligned: `textStyle.micro`, `text.muted`, tick icon | `chat.sent` |
| Pending (offline queue) | `surface.pending`, text `text.primary`, no shadow; status line `text.accent` + clock icon | `offline.queued` |
| Pending, older than 24 h | as pending, plus two link buttons under it | `offline.queued_old`, `offline.queued_send`, `offline.queued_delete` |
| Failed (Capsule could not answer) | Capsule bubble with body text + primary button with refresh icon | `error.connection_dropped`, `error.try_again` |
| Error on a message | Capsule bubble: `error.server.title` in `textStyle.subtitle`, body, primary button | `error.server.*`, `error.try_again` |
| Voice (user) | gradient bubble: mic icon, duration (`textStyle.bodyMedium`, tabular figures). Under the bubble, right-aligned: `voice.transcript_label` + transcript (`textStyle.caption`, `text.secondary`), then the `voice.edit` text link until Capsule answers. No play button. | `voice.transcribing` while waiting |
| Photo uploading (user) | local preview 220 × 220, radius `xl`, 4 px `surface.card` border, `shadow.md`; progress bar along the bottom (`control.progressTrack` / `control.progressFill`) | — |
| Photo sent (user) | neutral photo icon (24, `icon.onBrand`) in a gradient bubble + garment count; the preview is removed | `a11y.msg_photo` |
| Garments found (Capsule) | Capsule bubble with rows on `surface.sunken`, radius `md`, padding `space.3`: checkbox, garment name `textStyle.labelSmall`, status `textStyle.micro` `text.link` with tick (`photo.item.in_look`) or `text.muted` (`photo.item.not_used`); then `photo.privacy_note` in `textStyle.caption`, `text.muted` | `photo.item.*`, `photo.privacy_note` |
| Stopped | Capsule bubble, `text.secondary` | `chat.stopped` + `error.try_again` |
| Date separator | centred chip: `textStyle.micro`, `text.muted`, `surface.timestamp`, radius `sm`, padding `space.1` / `space.3` | — |

Accessibility: each bubble is one focus stop (`a11y.msg_capsule`, `a11y.msg_user`, `a11y.msg_voice`, `a11y.msg_photo`); its status line is read with it. New Capsule bubbles are announced politely.

## 4. Status line and typing indicator

- **Header status** (`chat.status.thinking`, `chat.status.preparing`, `chat.status.reading_photo`): replaces the header subtitle; `textStyle.micro`, `text.link`; live region.
- **Typing indicator:** a Capsule bubble with three 8 px dots in `primitive.color.rust.500`, `primitive.color.berry.500` and `primitive.color.plum.500` (decorative, hidden from screen readers), looping over `motion.duration.typingLoop`. With Reduce Motion the dots stay still.

## 5. Progress steps (C2)

A Capsule bubble listing the steps from flows.md (`guide.progress.*`) in order.

| Step state | Indicator (22 circle) | Text |
| --- | --- | --- |
| Done | `status.success.bg` circle with tick `status.success.fg` | `textStyle.bodySmall`, `text.primary` |
| Active | 22 spinner ring 2.5 px: track `control.progressTrack`, arc `control.progressFill`; static with Reduce Motion | `textStyle.bodySmall`, `text.primary`, weight `semibold` |
| Pending | not shown (steps appear as they start) | — |

Under the steps, a skeleton of the guide card (§17) shows while the guide streams in. `chat.stop` is a Secondary button with a stop icon, placed after the steps and before the composer in focus order (`a11y.stop`). Each completed step is announced once; `a11y.guide_ready` is announced at the end.

## 6. Guide card in chat and saved guide row

Used in chat after a guide is ready, in C3 (saved guides offline) and as the L1 row.

| Part | Value |
| --- | --- |
| Surface | `surface.card`, radius `xl`, padding `space.4`, `shadow.md` |
| Leading tile | 56 square, radius `md`, `gradient.brand`, hanger icon `icon.onBrand` (decorative) |
| Eyebrow (optional) | `textStyle.eyebrow`, `text.accent`, download icon 13: `guide.on_device` |
| Title | `textStyle.subtitle`, `text.primary` (occasion title) |
| Summary | `textStyle.bodySmall`, `text.secondary`: `saved.row.summary` |
| Trailing | chevron 24 `icon.brand` (decorative) |
| Pressed | `surface.pressed` |
| Focus | ring around the card |
| Disabled | not used; offline saved guides always open |

Accessibility: one focus stop, role `button`; reads title, summary, badge. In L1, delete is a custom action ("More", `a11y.more_guide` → `saved.delete.action`).

## 7. Guide item card

| Part | Value |
| --- | --- |
| Surface | `surface.card`, radius `xl`, padding `space.4`, gap `space.4`, `shadow.md` |
| Image | `size.itemImageWidth` × `size.itemImageHeight`, radius `md`; product image, decorative |
| Name (H3) | `textStyle.subtitle`, `text.primary` |
| Price | `textStyle.subtitle`, `text.primary`, tabular figures, right-aligned; moves under the name from font scale 1.5 |
| Reason | `textStyle.bodySmall`, `text.secondary` |
| Action | link button `guide.item.view`, or the owned badge (§16) `guide.item.owned` |

| State | Spec |
| --- | --- |
| Default (shop item) | as above |
| Owned (from the user's photo) | price "€0"; badge `guide.item.owned` with camera icon instead of the link button |
| Image missing | `gradient.placeholder` box with a 44 neutral garment icon (`icon.muted`) |
| Unavailable / price changed | reason replaced by `guide.item.unavailable` in `textStyle.bodySmall`, `text.accent`, with an alert icon; the link button becomes `guide.item.find_alternative` |
| Offline | `guide.item.view` disabled; `offline.link_disabled` under it in `textStyle.caption`, `text.muted` |
| Pressed / focus | the card itself is not pressable; only the link button is |
| Loading | skeleton (§17): image box + three bars |

Accessibility: one focus stop for name, price and reason, then the link button (`a11y.item_link`). Name is heading level 3.

## 8. Section header (guide)

Number badge `size.stepBadge` circle, `gradient.brand`, digit `textStyle.labelSmall` `text.onBrand`, decorative. Title `textStyle.heading` `text.primary` (H2) and sub `textStyle.caption` `text.secondary` (`guide.section.*.sub`). Gap `space.3`; `space.6` above the section. The number repeats the order; the order itself is carried by the heading text.

## 9. Budget bar

Lives in the guide summary on `surface.sunken`, radius `lg`, padding `space.4`, gap `space.3`.

| Part | Value |
| --- | --- |
| Row | `guide.budget.label` (`textStyle.labelSmall`, `text.secondary`) and `guide.budget.amount`: total in `textStyle.subtitle` `text.primary`, "of {budget}" in `text.muted` weight `medium`; tabular figures. Stacks from font scale 1.5 |
| Bar | height `size.budgetBarHeight`, radius `pill`, track `budget.track`, fill `gradient.budget` to total ÷ budget |
| Within budget | tick icon 16 + `guide.budget.checked`, `textStyle.micro`, `status.success.fg` |
| Over budget | bar full in `budget.over`; alert icon + `guide.budget.over` in `status.warning.fg` |
| Loading | skeleton bar and two text bars |

The bar is decorative. Screen readers get one text equivalent: `a11y.budget_summary` or `a11y.budget_summary_over`. Numbers come from the budget validator, never from model text. The fill animates once over `motion.duration.slow` (no animation with Reduce Motion).

## 10. Banner

Full-width card at the top of the content, under the header.

| Part | Value |
| --- | --- |
| Surface | `surface.card`, radius `xl`, padding `space.4`, gap `space.3`, `shadow.md` |
| Icon tile | `size.iconTile`, radius `md`; colours by variant below; icon 20, decorative |
| Text | lead in `textStyle.subtitle` `text.primary` (inline bold for the first sentence where the copy has one), body `textStyle.body` `text.secondary` |
| Actions | optional, Primary + Secondary stacked or in a row (stack from font scale 1.5) |

| Variant | Tile | Copy | Behaviour |
| --- | --- | --- | --- |
| Offline | `status.warning.bg` + no-wifi icon `status.warning.fg` | `offline.banner` | Appears when offline, announced once (polite); disappears when back online and `offline.back_online` is announced. Not dismissible. Also `offline.refresh_disabled` in L1 |
| Error (server unreachable, refresh failed) | `status.error.bg` + alert icon `status.error.fg` | `error.server.title` + `error.server.body` + `error.try_again`; `error.saved.refresh` + `error.try_again` | Inline above cached content; never replaces it |
| Return banner (L1) | `status.info.bg` + phone icon `status.info.fg` | `saved.return_banner.*` | Primary `saved.return_banner.create`, Secondary `saved.return_banner.dismiss`; either dismisses for good |
| Info / reason | `status.info.bg` + info icon | `save.sheet.offline`, `privacy.delete.offline`, `offline.welcome` | Inline in a sheet or screen |

States: banners themselves are not pressable. Their buttons follow §1. Focus moves to a banner only when the user navigates to it, never automatically.

## 11. Input bar (composer)

| Part | Value |
| --- | --- |
| Container | pill on `surface.card`, radius `pill`, padding `space.1`, gap `space.1`, `shadow.lg`; min height `size.composerMinHeight`; screen padding `space.2` / `space.3`, plus the bottom safe area |
| Order | camera (`a11y.camera`) · text field · mic (`a11y.mic`) · send (`a11y.send`) |
| Field | `textStyle.bodyMedium`, `text.primary`; placeholder `text.placeholder` (`chat.composer.placeholder`); grows to 4 lines, then scrolls |

| State | Spec |
| --- | --- |
| Empty | send disabled (`surface.disabled`, arrow `text.disabled`); mic enabled |
| Typing | send enabled (gradient) |
| Busy (guide generating) | placeholder `chat.composer.placeholder_busy`; field active |
| Offline | placeholder `chat.composer.placeholder_offline`; camera and mic disabled (`icon.muted`, hint `offline.media_disabled`); send enabled and queues |
| Recording | the field area shows a live dot `status.warning.fg` + `voice.recording` + timer (`textStyle.bodyMedium`, tabular) + waveform (`icon.brand`, decorative, static with Reduce Motion); `voice.cancel` text link; mic becomes stop (`a11y.mic_stop`) as the gradient circle |
| Recording too short | toast (§13) `voice.too_short` |
| Pressed / focus | per icon button; the field shows the focus ring on the whole pill when focused by keyboard |

At 200 % text the field grows; the icon buttons keep their size and stay bottom-aligned.

## 12. Form controls

### Switch row (O2, S1)
Row on `surface.card` (rows are grouped in a card, radius `xl`, padding `space.4`). Label `textStyle.subtitle` `text.primary` (`onb.consent.*.label`), description `textStyle.bodySmall` `text.secondary` (`onb.consent.*.desc`), and a native switch on the trailing side, top-aligned.
- Track on `control.switchOn`, off `control.switchOff`, thumb `control.thumb`. The native switch shape (thumb position) also shows the state.
- Pressed: the row shows `surface.pressed`. Disabled: label and description `text.disabled`, track `surface.disabled`. Focus: ring around the whole row.
- One focus stop per row: "Crash reports, off, switch" + description. Both start **off**.

### Radio row (O3 wardrobe, W1)
Full-width row, height ≥ 56, `surface.card`, 1 px `border.control`, radius `lg`, padding `space.4`. Label `textStyle.subtitle`, description `textStyle.bodySmall` `text.secondary`. Trailing 24 radio: off = 2 px `border.control` ring; on = `gradient.brand` filled circle with a white tick.
- Selected: border 2 px `focus.ring` colour + filled radio; `wardrobe.change.current` as a `textStyle.micro` `text.link` badge on the current one in W1.
- Pressed `surface.pressed`; disabled not used; focus ring around the row. Role `radio` in a radio group; `onb.wardrobe.helper` is read before the options.

### Checkbox row (untick a photo garment, `wardrobe.change.make_default`)
24 box, radius 6, 2 px `border.control` when off; `gradient.brand` with a white tick when on. Label `textStyle.labelSmall` `text.primary`. Row hit ≥ 48. Role `checkbox`.

### Segmented control (O5 size system: EU / UK / US)
Pill on `surface.sunken`, padding `space.1`; segments ≥ 44 high, `textStyle.labelSmall`. Selected segment: `surface.card`, `shadow.sm`, label `text.primary`, weight `bold`. Unselected: label `text.secondary`. Each segment is a labelled radio. Focus ring per segment.

### Picker row (O5 sizes)
Row ≥ 56: label `textStyle.subtitle` (`onb.sizes.tops` …), value `textStyle.body` `text.secondary` (`onb.sizes.not_set` when empty), chevron. Opens the native picker. Accessible label `a11y.size_picker`. Pressed `surface.pressed`; focus ring around the row.

## 13. Sheets, dialogs, toasts

| Component | Spec |
| --- | --- |
| Bottom sheet (A1 save, W1 wardrobe, P1 permission) | `surface.card`, top corners `xl`, padding `space.6` / `space.4`, `shadow.lg`, grab handle 36 × 4 `border.control` (decorative). Scrim `surface.scrim`. Title `textStyle.title`, body `textStyle.body` `text.secondary`, warning text (`save.sheet.local_warning`) `textStyle.bodySmall` `text.secondary`. Actions full width, stacked, ≥ 48. Close icon button `a11y.close` top-right. Swipe down, close and Android back all mean the sheet's dismiss action (flows.md A1). The sheet takes focus and its title is read first. At 200 % the sheet scrolls; actions stay reachable at the end. |
| Confirm dialog (`saved.delete.*`, `privacy.delete.*`) | Native alert on both platforms (HIG / Material). Title and body from the copy deck; buttons `saved.delete.cancel` and the destructive confirm. The cancel option is the default. |
| Action sheet (`photo.source.*`) | Native action sheet / bottom menu. |
| Toast (`save.done_account`, `save.done_local`, `voice.too_short`, `privacy.delete.done`) | `surface.card`, radius `xl`, `shadow.lg`, padding `space.3` / `space.4`; leading status icon; `textStyle.bodySmall` `text.primary`. Above the composer or bottom safe area. Shows for at least 4 s, plus 1 s per 10 words over 20; announced politely; never holds an action that exists nowhere else. |

## 14. Feedback (thumbs up / thumbs down)

`guide.feedback.question` in `textStyle.subtitle`. Two icon toggle buttons in a row, gap `space.3`; each a 48 circle on `surface.card` with 1 px `border.control` and a 24 icon in `icon.default`.
- Selected: `gradient.brand`, icon `icon.onBrand` filled, `shadow.brand`; the other stays unselected. `guide.feedback.thanks` appears as text under the row (`textStyle.bodySmall`, `text.secondary`), announced politely.
- After a thumbs-down: feedback reason chips (§2) under `guide.feedback.reason_title`.
- Pressed `surface.pressed`; disabled not used (feedback queues offline); focus ring per button.
- Labels `a11y.helpful_yes` / `a11y.helpful_no`, role `button` with `selected` state.

## 15. Header

| Variant | Spec |
| --- | --- |
| Chat | `surface.header`, `shadow.header`, padding `space.2`. Left: `a11y.menu`. Centre: one button (`a11y.wardrobe_button`) with title "Capsule" (`textStyle.headerTitle`, `text.primary`) over the subtitle (`textStyle.caption`, `text.muted`: `chat.header.subtitle` / `chat.header.subtitle_wardrobe`, or the live status per §4). Right: `a11y.new_chat`. |
| Guide | Back (`a11y.back`), centred `guide.title` (`textStyle.headerTitle`), share (`a11y.share`). |
| Sheet / onboarding | Back on O3–O5; `onb.progress` in `textStyle.micro` `text.muted`. |

The header title wraps to 2 lines at large text sizes; icon buttons keep 48.

## 16. Badge and tag

Non-interactive labels. Height grows with text; padding `space.1` / `space.2` (canvas 5/9); radius `sm`.

| Badge | Surface | Text | Icon |
| --- | --- | --- | --- |
| Owned (`guide.item.owned`) | `surface.tag` | `textStyle.micro`, `text.link` | camera 13 |
| On this phone (`guide.on_device`) | none (eyebrow) or `status.warning.bg` in L1 rows | `textStyle.eyebrow` / `micro`, `text.accent` | download 13 |
| Current (`wardrobe.change.current`) | `surface.tag` | `textStyle.micro`, `text.link` | tick 13 |
| Sent / queued status lines | none | `textStyle.micro`, `text.muted` / `text.accent` | tick / clock 14 |

## 17. Skeleton and placeholders

Blocks filled with `gradient.placeholder`, radius `sm` for text bars (12 high) and `md` for images, widths 92 % / 76 % / 52 %. They shimmer only without Reduce Motion (opacity 1 → 0.6 over `motion.duration.typingLoop`). Hidden from screen readers; the container is announced as "Loading" once. A skeleton is replaced in place; content never jumps under the user's finger.

## Coverage: flows.md states → components

| Screen / state (flows.md) | Component |
| --- | --- |
| O1 Welcome, offline note | Primary button; Info banner (`offline.welcome`) |
| O2 consent switches, allow / decline / save | Switch row; Secondary buttons (equal weight); Text link (`onb.consent.details_toggle`) |
| O3 wardrobe, nothing selected | Radio row; Primary disabled; Text link `onb.skip` |
| O4 style, max 3 | Multi chips; disabled chips + `onb.style.max` |
| O5 sizes | Segmented control; Picker row |
| C1 first run, examples | Capsule bubble; Suggestion chips |
| C1 follow-up, wardrobe asked once | Capsule bubble; Choice chips |
| C1 composer empty / typing / offline | Input bar states |
| C1 photo: preview, uploading, sent, found, failed, invalid, no clothes | Photo bubble states; Garments found rows; Error message bubble |
| C1 voice: recording, too short, transcribing, transcript, failed | Input bar Recording; Toast; Voice bubble; Error message bubble + `error.voice.type_instead` link button |
| C2 generating, stop, stopped, timeout, no fit | Status line; Progress steps; Skeleton; Secondary `chat.stop`; Capsule bubble with `error.guide.no_fit.*` as Suggestion-style choice chips |
| C3 offline, queued, queued > 24 h, connection dropped, back online | Offline banner; Pending bubble; Failed bubble |
| G1 guide: summary, budget within / over, sections, items (owned, missing image, unavailable, offline), why, feedback, save / saved, loading, error | Header; Budget bar; Section header; Guide item card states; Feedback; Primary `guide.save` → success badge `guide.saved`; Skeleton; Error banner |
| A1 save sheet, offline | Bottom sheet; Info banner `save.sheet.offline` |
| L1 saved: loading, empty, list, return banner, offline, refresh failed, delete | Skeleton; empty state (title `textStyle.title`, body, Primary `saved.empty.cta`); Guide card row; Return banner; Offline banner; Error banner; Confirm dialog |
| P1 permission reason, denied | Bottom sheet (Primary `perm.continue`, Secondary `perm.not_now`); Capsule bubble + Link button `perm.open_settings` |
| W1 change wardrobe | Bottom sheet; Radio rows; Checkbox row `wardrobe.change.make_default` |
| S1 privacy | Switch rows; Secondary / Destructive buttons; Confirm dialog; Info banner `privacy.delete.offline`; Toast `privacy.delete.done` |

## Contrast

Ratios use WCAG 2.x relative luminance, rounded to 2 decimals. The threshold is 4.5:1 for text (all text in this app is held to the normal-size threshold, including large text) and 3:1 for non-text (control edges, icons that carry meaning, focus ring, state indicators). Gradient pairs are checked at both ends and at the midpoint; the worst one counts.

Translucent surfaces: `surface.header` and `surface.timestamp` (light) are white over the background, so text on them is always at least as high as on `bg.bottom`, which is listed as the lower bound. Dark `surface.header` composites to at most the luminance of `night.700`, which is listed.

### Text, light theme

| Foreground | Background | Ratio | AA |
| --- | --- | --- | --- |
| text.primary #1E1A24 | surface.card #FFFFFF | 17.09 | pass |
| text.primary #1E1A24 | bg.top #FFF5EE | 15.91 | pass |
| text.primary #1E1A24 | bg.middle #FBEAE3 | 14.63 | pass |
| text.primary #1E1A24 | bg.bottom #F4E4EF | 13.99 | pass |
| text.primary #1E1A24 | surface.sunken #FBF2EE | 15.49 | pass |
| text.primary #1E1A24 | surface.tag / pressed #F5E7F0 | 14.30 | pass |
| text.primary #1E1A24 | surface.pending #EADCEB | 12.98 | pass |
| text.primary #1E1A24 | status.warning.bg #FBE7DF | 14.32 | pass |
| text.secondary #4F4855 | surface.card #FFFFFF | 8.79 | pass |
| text.secondary #4F4855 | bg.top #FFF5EE | 8.18 | pass |
| text.secondary #4F4855 | bg.middle #FBEAE3 | 7.52 | pass |
| text.secondary #4F4855 | bg.bottom #F4E4EF | 7.19 | pass |
| text.secondary #4F4855 | surface.sunken #FBF2EE | 7.96 | pass |
| text.secondary #4F4855 | surface.pending #EADCEB | 6.67 | pass |
| text.muted / placeholder #675F6C | surface.card #FFFFFF | 6.12 | pass |
| text.muted #675F6C | bg.top #FFF5EE | 5.70 | pass |
| text.muted #675F6C | bg.middle #FBEAE3 | 5.24 | pass |
| text.muted #675F6C | bg.bottom #F4E4EF | 5.01 | pass |
| text.muted #675F6C | surface.sunken #FBF2EE | 5.55 | pass |
| text.muted #675F6C | surface.tag #F5E7F0 | 5.12 | pass |
| text.disabled #675F6C | surface.disabled #EADCEB | 4.65 | pass |
| text.accent #A13F2B | surface.card #FFFFFF | 6.44 | pass |
| text.accent #A13F2B | bg.top #FFF5EE | 5.99 | pass |
| text.accent #A13F2B | bg.middle #FBEAE3 | 5.51 | pass |
| text.accent #A13F2B | bg.bottom #F4E4EF | 5.27 | pass |
| text.accent #A13F2B | surface.sunken #FBF2EE | 5.84 | pass |
| text.accent #A13F2B | status.warning.bg #FBE7DF | 5.40 | pass |
| text.accent #A13F2B | surface.tag #F5E7F0 | 5.39 | pass |
| text.link / status.success.fg #6B3A8A | surface.card #FFFFFF | 8.09 | pass |
| text.link #6B3A8A | bg.top #FFF5EE | 7.53 | pass |
| text.link #6B3A8A | bg.middle #FBEAE3 | 6.93 | pass |
| text.link #6B3A8A | bg.bottom #F4E4EF | 6.62 | pass |
| text.link #6B3A8A | surface.sunken #FBF2EE | 7.33 | pass |
| text.link #6B3A8A | surface.tag / pressed #F5E7F0 | 6.77 | pass |
| text.linkPressed #5E2E7A | surface.pressed #F5E7F0 | 8.18 | pass |
| text.onBrand #FFFFFF | gradient.brand start #BF4A33 | 4.95 | pass (worst) |
| text.onBrand #FFFFFF | gradient.brand midpoint #9C4468 | 6.10 | pass |
| text.onBrand #FFFFFF | gradient.brand end #7A3E9D | 6.99 | pass |
| text.onBrand #FFFFFF | brand start pressed (#BF4A33 + ink 12 % ≈ #AC4431) | 5.79 | pass |

### Text, dark theme

| Foreground | Background | Ratio | AA |
| --- | --- | --- | --- |
| text.primary #F7F1F5 | bg.top #1C1517 | 16.13 | pass |
| text.primary #F7F1F5 | bg.middle #1A1419 | 16.28 | pass |
| text.primary #F7F1F5 | bg.bottom #18131C | 16.41 | pass |
| text.primary #F7F1F5 | surface.header bound #1F1824 | 15.53 | pass |
| text.primary #F7F1F5 | surface.card #2A2230 | 13.76 | pass |
| text.primary #F7F1F5 | surface.sunken #231C28 | 14.87 | pass |
| text.primary #F7F1F5 | surface.tag / pending / pressed #3A2E44 | 11.40 | pass |
| text.primary #F7F1F5 | status.warning.bg #3D2420 | 12.81 | pass |
| text.secondary #D6CCD6 | bg.top #1C1517 | 11.52 | pass |
| text.secondary #D6CCD6 | surface.card #2A2230 | 9.83 | pass |
| text.secondary #D6CCD6 | surface.sunken #231C28 | 10.62 | pass |
| text.secondary #D6CCD6 | surface.pending #3A2E44 | 8.14 | pass |
| text.secondary #D6CCD6 | status.warning.bg #3D2420 | 9.15 | pass |
| text.muted / placeholder #B3A8B5 | bg.top #1C1517 | 7.86 | pass |
| text.muted #B3A8B5 | surface.header bound #1F1824 | 7.57 | pass |
| text.muted #B3A8B5 | surface.card / timestamp #2A2230 | 6.71 | pass |
| text.muted #B3A8B5 | surface.sunken #231C28 | 7.24 | pass |
| text.muted #B3A8B5 | surface.tag / pending #3A2E44 | 5.55 | pass |
| text.disabled #B3A8B5 | surface.disabled #2E2733 | 6.32 | pass |
| text.accent #F2A08A | bg.top #1C1517 | 8.71 | pass |
| text.accent #F2A08A | surface.card #2A2230 | 7.43 | pass |
| text.accent #F2A08A | surface.sunken #231C28 | 8.03 | pass |
| text.accent #F2A08A | status.warning.bg #3D2420 | 6.91 | pass |
| text.accent #F2A08A | surface.tag #3A2E44 | 6.15 | pass |
| text.link / status.success.fg #D4A8F0 | bg.top #1C1517 | 9.12 | pass |
| text.link #D4A8F0 | surface.header bound #1F1824 | 8.78 | pass |
| text.link #D4A8F0 | surface.card #2A2230 | 7.78 | pass |
| text.link #D4A8F0 | surface.sunken #231C28 | 8.41 | pass |
| text.link #D4A8F0 | surface.tag / pressed #3A2E44 | 6.44 | pass |
| text.onBrand #FFFFFF | gradient.brand start / mid / end | 4.95 / 6.10 / 6.99 | pass |

### Non-text (3:1)

| Element | Colour | Against | Light | Dark |
| --- | --- | --- | --- | --- |
| border.control | #8A8290 | surface.card | 3.70 (#FFFFFF) | 4.14 (#2A2230) |
| border.control | #8A8290 | bg (worst stop) | 3.03 (#F4E4EF) | 4.85 (#1C1517) |
| border.control | #8A8290 | surface.sunken | 3.35 (#FBF2EE) | 4.47 (#231C28) |
| border.control | #8A8290 | surface.pressed | 3.10 (#F5E7F0) | 3.43 (#3A2E44) |
| focus.ring | light #7A3E9D / dark #D4A8F0 | surface.card | 6.99 | 7.78 |
| focus.ring | same | bg (worst stop) | 5.72 | 9.12 |
| focus.ring | same | surface.sunken | 6.34 | 8.41 |
| icon.accent | light #BF4A33 / dark #F2A08A | surface.card | 4.95 | 7.43 |
| icon.accent | same | bg.bottom / bg.top | 4.05 | 8.71 |
| icon.accent | same | status.warning.bg | 4.15 | 6.91 |
| icon.brand | light #7A3E9D / dark #D4A8F0 | surface.card | 6.99 | 7.78 |
| icon.muted | light #675F6C / dark #B3A8B5 | surface.card | 6.12 | 6.71 |
| control.switchOn | light #7A3E9D / dark #A86BCF | surface.card | 6.99 | 4.14 |
| control.switchOn | same | bg (worst stop) | 5.72 | 4.85 |
| control.switchOff | #8A8290 | surface.card | 3.70 | 4.14 |
| control.thumb #FFFFFF | on switchOn | — | 6.99 | 3.70 |
| control.thumb #FFFFFF | on switchOff #8A8290 | — | 3.70 | 3.70 |
| control.progressFill vs progressTrack | light #7A3E9D on #EADCEB / dark #D4A8F0 on #3A2E44 | — | 5.31 | 6.44 |
| gradient.budget fill vs budget.track | light start #BF4A33 / mid #9C4468 / end #7A3E9D on #EFDFD9 | — | 3.83 / 4.72 / 5.40 | — |
| gradient.budget fill vs budget.track | dark start #D9684F / mid #C06A8F / end #A86BCF on #14101A | — | — | 5.40 / 5.10 / 5.07 |
| budget.over vs budget.track | light #A13F2B on #EFDFD9 / dark #F2A08A on #14101A | — | 4.98 | 9.10 |
| icon.onBrand (tick, send arrow) #FFFFFF | gradient.brand worst stop | — | 4.95 | 4.95 |

### Pairs that do not reach 3:1, and why that is acceptable

| Pair | Ratio | Why it is acceptable |
| --- | --- | --- |
| Dark theme: `gradient.brand` edge against the dark background (start #BF4A33 / mid #9C4468 / end #7A3E9D on #1C1517) | 3.63 / 2.94 / 2.57 | The gradient's edge does not identify the control: buttons and chips are identified by their text label (4.95:1 or more), so WCAG 1.4.11 does not require the boundary. |
| Dark theme: selected chip (`gradient.brand`) against unselected chip (`surface.card` #2A2230) | 2.19 at the plum end | The selected state is carried by the white tick icon (4.95:1 or more on the gradient) and the selected trait, not by the fill. |
| `border.control` against `surface.disabled` (#EADCEB) | 2.81 | Disabled controls are exempt; disabled buttons drop the border, and their text still passes. |
| Typing dots, waveform, avatar tile, image placeholders, skeletons | — | Decorative; status is given in text and announced. |

No text pair fails.

## Changes from the canvas, and why

| Canvas | Spec | Why |
| --- | --- | --- |
| Placeholder `#8A8290` | `text.placeholder` = #675F6C | #8A8290 is 3.0–3.7:1, which fails for text. |
| Eyebrows and on-device label `#9C3F43`, queued label `#8A3A2A` | `text.accent` #A13F2B | Owner decision: one accent text colour. It passes on every light surface. |
| Chips 40 high, link buttons 36 high | 44 visual, hit 48 | Touch targets of 44 pt / 48 dp or more. |
| Chip edge `rgba(30,26,36,0.10)`, link button edge `rgba(122,62,157,0.25)` | `border.control` #8A8290 (1 px) | Unselected controls need a 3:1 edge to be found by low-vision users; the old edges were about 1.1–1.5:1. |
| 11 px eyebrow and tags | 12 minimum (`micro`, `eyebrow`) | Readability at default size for ages up to 60. |
| Message and paragraph text 15/22 | `body` 16/24 | Comfortable default without relying on users enlarging text; matches Material body-large. |
| Spacing 6, 10, 14, 18 | 4-pt scale (8, 12, 16) | The card requires a 4-pt scale; at most a 2-pt shift. |
| 17 radii | 6 radii (`xs`–`xl`, `pill`) | Fewer values to implement; at most a 2-pt shift. |
| Header `backdrop-filter: blur(16px)` | Translucent colour only | Blur would need a new dependency for little gain. |
| Pending bubble text `#3A2F42` | `text.primary` | Pending is shown by the surface and the `offline.queued` label, not by weaker text. |
| No pressed, focus or disabled styles | Defined for every component | Required by the card and by HIG / Material. |
| "S" / "C" avatar beside bubbles | No avatar; tail only | The header names Capsule (flows.md); fewer elements at 200 % text. |
| Plum shadows | Same in light; neutral black in dark | Plum is invisible on dark surfaces. |

## Open questions

1. **Gradients need `expo-linear-gradient`** (an Expo SDK module). It is still a new dependency under the root rules, so it needs an ADR in the E1 mobile card. The other option is SVG gradients via `react-native-svg`, which would also be new.
2. **Multi-layer shadows** use React Native's `boxShadow` style, which needs the New Architecture. If it is not available, use the layer at `singleLayerFallback` on iOS and `androidElevation` on Android; Android elevation shadows are grey, not plum. Mobile-engineer to confirm.
3. **Body 16 instead of the canvas's 15:** owner to confirm.
4. **Visible chip and button borders** (`border.control`) are heavier than the canvas. The alternative is no border (WCAG allows text to identify a control), but that is weaker for low-vision users. Owner to confirm.
5. **Usability test (E3):** include at least one participant using dark theme and one at 200 % text.
