# Wireframes: onboarding, save, saved guides

Low fidelity. They fix content, order, hierarchy and controls; visual style follows `apps/mobile/CLAUDE.md` and, later, the E0-09 tokens. Chat and guide are on the canvas (`reference/*.png`) and are not redrawn here, except the first-run chat state.

Format: ASCII boxes in markdown, chosen so a PR shows line-by-line diffs and every reviewer (human or agent) can read them without a design tool. Text in `[ ]` is a button, `( )` a radio, `[x]`/`[ ]` a checkbox or chip, `<id>` a copy id from `copy-deck.md`. Flow and states: `flows.md`.

Layout rules for all screens below:
- Single column, 20 pt side margins, content scrolls; the primary button is pinned to the bottom above the safe area and stays reachable at 200 % text.
- Progress "Step n of 3" appears on O3–O5 only (consent and welcome are not "steps" the user must finish).
- Back (top left, `a11y.back`) on O3–O5.

## O1 Welcome

```
+------------------------------------+
|                                    |
|  [neutral illustration: hanger +   |
|   chat bubble, no people]          |
|                                    |
|  <onb.welcome.title>               |
|  Your stylist for any occasion     |
|                                    |
|  <onb.welcome.body>                |
|  - Tell me the occasion and budget |
|  - I'll reuse clothes you own      |
|  - The total always fits budget    |
|                                    |
|                                    |
| [ Get started                    ] |
|  <onb.welcome.legal> (small text,  |
|   links: Terms, Privacy)           |
+------------------------------------+
```

Notes: no sign-in button here (guest first). Existing users sign in from the menu later (E1). If offline: `offline.banner` at top; "Get started" still works.

## O2 Analytics consent

```
+------------------------------------+
|  <onb.consent.title>               |
|  Help us improve Capsule?          |
|                                    |
|  <onb.consent.body>                |
|                                    |
|  [ What we collect  v ]            |
|  +------------------------------+  |
|  | <onb.consent.details>        |  |
|  | (expanded inline when tapped)|  |
|  +------------------------------+  |
|                                    |
|  <onb.consent.change_later>        |
|                                    |
| [ Allow                          ] |
| [ Not now                        ] |
+------------------------------------+
```

Notes: both buttons full width and equal size; no pre-ticked choice; no event fires until one is tapped. "Not now" never reappears as a nag; the switch lives in Settings → Privacy.

## O3 Wardrobe

```
+------------------------------------+
| <-                    Step 1 of 3  |
|                                    |
|  <onb.wardrobe.title>              |
|  Which wardrobe should I shop for? |
|  <onb.wardrobe.helper>             |
|                                    |
| +--------------------------------+ |
| | ( ) Menswear                   | |
| |     <onb.wardrobe.men.desc>    | |
| +--------------------------------+ |
| | ( ) Womenswear                 | |
| |     <onb.wardrobe.women.desc>  | |
| +--------------------------------+ |
| | ( ) Unisex                     | |
| |     <onb.wardrobe.unisex.desc> | |
| +--------------------------------+ |
|                                    |
| [ Continue                       ] |  disabled until a choice
| [ Skip for now ]  (text button)    |
+------------------------------------+
```

Notes: options are equal rows in this fixed order, none preselected. Selected row: brand-gradient border + tick + "selected" state. Skipping sets wardrobe = none; Capsule asks once in chat when it needs it.

## O4 Style

```
+------------------------------------+
| <-                    Step 2 of 3  |
|                                    |
|  <onb.style.title>                 |
|  <onb.style.helper>  (up to 3)     |
|                                    |
|  [ ] Classic    [ ] Relaxed        |
|  [ ] Minimal    [ ] Smart casual   |
|  [ ] Sporty     [ ] Colourful      |
|  [ ] Outdoor    [ ] Vintage        |
|                                    |
|  [ ] Not sure yet                  |
|                                    |
| [ Continue                       ] |
| [ Skip for now ]                   |
+------------------------------------+
```

Notes: chips wrap; at 200 % text they become one per line. "Not sure yet" clears and disables the others. Style names apply to any wardrobe; no gendered labels.

## O5 Sizes

```
+------------------------------------+
| <-                    Step 3 of 3  |
|                                    |
|  <onb.sizes.title>                 |
|  <onb.sizes.helper>                |
|                                    |
|  Size system  [ EU | UK | US ]     |
|                                    |
|  Tops          [ Not set      v ]  |
|  Bottoms       [ Not set      v ]  |
|  Shoes         [ Not set      v ]  |
|                                    |
|  <onb.sizes.privacy>               |
|                                    |
| [ Continue                       ] |
| [ Skip for now ]                   |
+------------------------------------+
```

Notes: pickers, not text fields. Tops: XXS–4XL; bottoms: letter or waist number for the chosen system; shoes: system-specific numbers incl. half sizes. Default system from device region (UK → UK, US → US, else EU), always changeable. "Continue" is enabled with any number of sizes set, including none. At ≥ 150 % text, label sits above its picker.

## C1 Chat, first run (empty)

```
+------------------------------------+
| [=]  (C) Capsule               [+] |
|          AI stylist · Menswear >   |
|------------------------------------|
|                                    |
| (C) <chat.empty.greeting>          |
|     Hi! Tell me where you're       |
|     headed and your budget. ...    |
|                                    |
|     <chat.empty.examples_label>    |
|     [ Job interview, €100       ]  |
|     [ Summer wedding guest, €150]  |
|     [ First date, €60           ]  |
|                                    |
|                                    |
| +--------------------------------+ |
| | [cam]  <placeholder>  [mic] [^]| |
| +--------------------------------+ |
+------------------------------------+
```

Notes: example prompts fill the composer (they do not send), so the user edits the budget. Wardrobe label in the header is shown only if chosen; tapping it opens F9. If wardrobe was skipped, the header shows "AI stylist" only.

## P1 Permission reason sheet (camera / photos / microphone)

```
+------------------------------------+
|  (chat, dimmed)                    |
|                                    |
| +--------------------------------+ |
| |                            [X] | |
| |  <perm.camera.title>           | |
| |  <perm.camera.body>            | |
| |                                | |
| | [ Continue                   ] | |  -> OS prompt
| | [ Not now ]                    | |
| +--------------------------------+ |
+------------------------------------+
```

Denied variant: body becomes `perm.*.denied`, primary becomes "Open Settings", secondary "Not now". Shown only when the user taps camera / mic, never at launch.

## A1 Save sheet (guest)

```
+------------------------------------+
|  (guide, dimmed)                   |
| +--------------------------------+ |
| |                            [X] | |
| |  <save.sheet.title>            | |
| |  Keep this guide?              | |
| |  <save.sheet.body>             | |
| |  - On any phone                | |
| |  - Safe if you delete the app  | |
| |                                | |
| | [ Create account             ] | |
| | [ Keep on this phone only    ] | |
| |  <save.sheet.local_warning>    | |
| +--------------------------------+ |
+------------------------------------+
```

Offline variant: `save.sheet.offline` replaces the body; "Create account" disabled with that reason; "Keep on this phone only" enabled.

## L1 Saved guides

```
+------------------------------------+
| <-        Saved guides             |
|------------------------------------|
| +--------------------------------+ |
| | <saved.return_banner.title>    | |  guest, shown once
| | <saved.return_banner.body>     | |
| | [ Create account ] [ Not now ] | |
| +--------------------------------+ |
|                                    |
| +--------------------------------+ |
| | [hanger] Date night, Saturday  | |
| |          12 Oct · 5 pieces     | |
| |          €89 of €100           | |
| |          On this phone     [...] |
| +--------------------------------+ |
| +--------------------------------+ |
| | [hanger] Job interview         | |
| |          3 Oct · 4 pieces  [...] |
| |          €96 of €100           | |
| +--------------------------------+ |
+------------------------------------+
```

Empty:

```
+------------------------------------+
| <-        Saved guides             |
|------------------------------------|
|                                    |
|        [hanger icon]               |
|  <saved.empty.title>               |
|  <saved.empty.body>                |
|                                    |
|  [ Start a guide ]                 |
|                                    |
+------------------------------------+
```

## F9 Change wardrobe sheet (from a guide)

```
+------------------------------------+
| +--------------------------------+ |
| |  <wardrobe.change.title_guide> | |
| |  <wardrobe.change.helper>      | |
| |  ( ) Menswear       (current)  | |
| |  ( ) Womenswear                | |
| |  ( ) Unisex                    | |
| |  [ ] <wardrobe.change.         | |
| |       make_default>            | |
| | [ Make a new guide           ] | |
| | [ Cancel ]                     | |
| +--------------------------------+ |
+------------------------------------+
```

From the chat header or Settings the title is `wardrobe.change.title_profile`, there is no checkbox, and the primary button is "Save".
