# Wireframes: onboarding, save, saved guides

Low fidelity. They fix content, order, hierarchy and controls; visual style follows `apps/mobile/CLAUDE.md` and, later, the E0-09 tokens. Chat and guide are on the canvas ([reference/](reference/)) and are not redrawn here, except the first-run chat state.

Format: ASCII boxes in markdown, chosen so a PR shows line-by-line diffs and every reviewer (human or agent) can read them without a design tool. `[ ]` is a button, `( )` a radio, `[x]`/`[ ]` before a label a checkbox or chip, `[on|off]` a switch, `<id>` a copy id from [copy-deck.md](copy-deck.md). Sample text under an id shows the current wording for orientation only. Flows and states: [flows.md](flows.md).

Layout rules for all screens:
- Single column, 20 pt side margins, content scrolls; primary buttons are pinned to the bottom above the safe area and stay reachable at 200 % text.
- `<onb.progress>` appears on O3–O5 only.
- Back (top left, `<a11y.back>`) on O3–O5.

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
|                                    |
|  <offline.welcome>  (offline only) |
|                                    |
| [ <onb.welcome.cta>              ] |
|  <onb.welcome.legal> (small text,  |
|   links: Terms, Privacy notice)    |
+------------------------------------+
```

Notes: no sign-in button here (guest first); existing users sign in from the menu (E1).

## O2 Privacy choices

```
+------------------------------------+
|  <onb.consent.title>               |
|  Help us improve Capsule?          |
|                                    |
|  <onb.consent.body>                |
|                                    |
| +--------------------------------+ |
| | <onb.consent.crash.label>      | |
| | <onb.consent.crash.desc>       | |
| |                       [on|off] | |  off by default
| +--------------------------------+ |
| | <onb.consent.usage.label>      | |
| | <onb.consent.usage.desc>       | |
| |                       [on|off] | |  off by default
| +--------------------------------+ |
|                                    |
|  [ <onb.consent.details_toggle> v ]|
|  <onb.consent.details> (inline     |
|   when expanded)                   |
|                                    |
|  <onb.consent.change_later>        |
|                                    |
| [ <onb.consent.allow>            ] |
| [ <onb.consent.decline>          ] |  becomes <onb.consent.save>
+------------------------------------+  once any switch is on
```

Notes: both buttons have the same size and the same visual style, stacked, ≥ 48 dp. Neither SDK starts before one is tapped. No nag later; the switches live in Settings › Privacy.

## O3 Wardrobe

```
+------------------------------------+
| <-              <onb.progress> 1/3 |
|                                    |
|  <onb.wardrobe.title>              |
|  Which wardrobe should I shop for? |
|  <onb.wardrobe.helper>             |
|                                    |
| +--------------------------------+ |
| | ( ) <onb.wardrobe.men>         | |
| |     <onb.wardrobe.men.desc>    | |
| +--------------------------------+ |
| | ( ) <onb.wardrobe.women>       | |
| |     <onb.wardrobe.women.desc>  | |
| +--------------------------------+ |
| | ( ) <onb.wardrobe.unisex>      | |
| |     <onb.wardrobe.unisex.desc> | |
| +--------------------------------+ |
|                                    |
| [ <onb.continue>                 ] |  disabled until a choice
| [ <onb.skip> ]  (text button)      |
+------------------------------------+
```

Notes: equal rows in this fixed order, none preselected. Selected row: brand-gradient border + tick + "selected" state. Skipping sets no wardrobe; Capsule asks once in chat when it needs it.

## O4 Style

```
+------------------------------------+
| <-              <onb.progress> 2/3 |
|                                    |
|  <onb.style.title>                 |
|  <onb.style.helper>                |
|                                    |
|  <onb.style.options>               |
|  [ ] Classic    [ ] Relaxed        |
|  [ ] Minimal    [ ] Smart casual   |
|  [ ] Sporty     [ ] Colourful      |
|  [ ] Outdoor    [ ] Vintage        |
|                                    |
|  <onb.style.max>  (when 3 chosen)  |
|                                    |
| [ <onb.continue>                 ] |  enabled with 0–3 chosen
| [ <onb.skip> ]                     |
+------------------------------------+
```

Notes: chips wrap; at 200 % text they become one per line. Style names apply to any wardrobe; no gendered labels.

## O5 Sizes

```
+------------------------------------+
| <-              <onb.progress> 3/3 |
|                                    |
|  <onb.sizes.title>                 |
|  <onb.sizes.helper>                |
|                                    |
|  <onb.sizes.system> [ EU | UK | US ]|
|                                    |
|  <onb.sizes.tops>    [<onb.sizes.not_set> v]
|  <onb.sizes.bottoms> [<onb.sizes.not_set> v]
|  <onb.sizes.shoes>   [<onb.sizes.not_set> v]
|                                    |
|  <onb.sizes.privacy>               |
|                                    |
| [ <onb.continue>                 ] |
| [ <onb.skip> ]                     |
+------------------------------------+
```

Notes: pickers, not text fields. Tops XXS–4XL; bottoms letter or waist number for the chosen system; shoes system-specific numbers incl. half sizes. Default system from device region (UK → UK, US → US, else EU), always changeable. `<onb.continue>` works with any number of sizes set, including none. At ≥ 150 % text each label sits above its picker.

## C1 Chat, first run (empty)

```
+------------------------------------+
| [=]  (C) Capsule               [+] |
|          <chat.header.subtitle_    |
|           wardrobe>                |  whole title block = button to W1
|------------------------------------|
|                                    |
| (C) <chat.empty.greeting>          |
|                                    |
|     <chat.empty.examples_label>    |
|     [ <chat.empty.example_1>    ]  |
|     [ <chat.empty.example_2>    ]  |
|     [ <chat.empty.example_3>    ]  |
|                                    |
| +--------------------------------+ |
| | [cam] <chat.composer.          | |
| |        placeholder> [mic] [^]  | |
| +--------------------------------+ |
+------------------------------------+
```

Notes: examples fill the composer (they do not send), so the user can edit the budget. If the wardrobe was skipped, the subtitle is `<chat.header.subtitle>`. Icons: `<a11y.menu>`, `<a11y.new_chat>`, `<a11y.camera>`, `<a11y.mic>`, `<a11y.send>`.

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
| | [ <perm.continue>            ] | |  -> OS prompt
| | [ <perm.not_now>             ] | |
| +--------------------------------+ |
+------------------------------------+
```

Photos use `<perm.photos.title>` / `<perm.photos.body>`; microphone uses `<perm.mic.title>` / `<perm.mic.body>`. Denied variant: body becomes `<perm.camera.denied>`, `<perm.photos.denied>` or `<perm.mic.denied>`, primary becomes `<perm.open_settings>`. Shown only when the user taps camera or mic, never at launch.

## A1 Save sheet (guest)

```
+------------------------------------+
|  (guide, dimmed)                   |
| +--------------------------------+ |
| |                            [X] | |
| |  <save.sheet.title>            | |
| |  Keep this guide?              | |
| |  <save.sheet.body>             | |
| |                                | |
| | [ <save.sheet.create>        ] | |
| | [ <save.sheet.local>         ] | |
| |  <save.sheet.local_warning>    | |
| +--------------------------------+ |
+------------------------------------+
```

Offline variant: `<save.sheet.offline>` replaces the body; `<save.sheet.create>` disabled with that reason; `<save.sheet.local>` enabled.

## L1 Saved guides

```
+------------------------------------+
| <-        <saved.title>            |
|------------------------------------|
| +--------------------------------+ |
| | <saved.return_banner.title>    | |  guest, once (trigger: flows F6)
| | <saved.return_banner.body>     | |
| | [<saved.return_banner.create>] | |
| | [<saved.return_banner.dismiss>]| |
| +--------------------------------+ |
|                                    |
| +--------------------------------+ |
| | [hanger] Date night, Saturday  | |
| |          12 Oct                | |
| |          <saved.row.summary>   | |
| |          <guide.on_device> [...] |
| +--------------------------------+ |
| +--------------------------------+ |
| | [hanger] Job interview         | |
| |          3 Oct           [...] | |
| |          <saved.row.summary>   | |
| +--------------------------------+ |
+------------------------------------+
```

`[...]` = `<a11y.more_guide>`.

Empty:

```
+------------------------------------+
| <-        <saved.title>            |
|------------------------------------|
|                                    |
|        [hanger icon]               |
|  <saved.empty.title>               |
|  <saved.empty.body>                |
|                                    |
|  [ <saved.empty.cta> ]             |
|                                    |
+------------------------------------+
```

## W1 Change wardrobe sheet (from a guide)

```
+------------------------------------+
| +--------------------------------+ |
| |  <wardrobe.change.title_guide> | |
| |  <wardrobe.change.helper>      | |
| |  ( ) Menswear                  | |
| |      <wardrobe.change.current> | |
| |  ( ) Womenswear                | |
| |  ( ) Unisex                    | |
| |  [ ] <wardrobe.change.         | |
| |       make_default>            | |
| | [ <wardrobe.change.cta_guide>] | |
| | [ <wardrobe.change.cancel>   ] | |
| +--------------------------------+ |
+------------------------------------+
```

From the chat header or Settings: title `<wardrobe.change.title_profile>`, helper `<wardrobe.change.helper_profile>`, no checkbox, primary `<wardrobe.change.cta_profile>`.
