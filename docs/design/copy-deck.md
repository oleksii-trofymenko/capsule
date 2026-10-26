# Copy deck (en-GB)

Every string used by [flows.md](flows.md) and [onboarding-wireframes.md](onboarding-wireframes.md). Specs reference the id; change wording here only.

## Voice and tone

- Capsule speaks as "I"; the user is "you". Plain words, short sentences, British spelling (colour, personalise, organise).
- Confident and explains why. No youth slang, no emoji in Capsule's text, no exclamation marks except the greeting.
- Never comment on bodies, age or appearance. Talk about garments, colours, occasions and budget.
- Never promise more than the system guarantees (media deletion within 24 h, budget checked by code, guest data retention).
- Prices: "€48", "€89 of €100" (symbol first, no space, no decimals for whole euros; "€12.50" otherwise). Formatted by locale in code.
- Buttons are verbs ("Create account", "Try again"); no "OK" or "Submit".
- `{name}` placeholders are filled by code. Budget numbers always come from the budget validator, never from model text.

## Global and accessibility labels

| Id | Text |
| --- | --- |
| `chat.header.subtitle` | AI stylist |
| `chat.header.subtitle_wardrobe` | AI stylist · {wardrobe} |
| `chat.status.thinking` | Thinking… |
| `chat.status.preparing` | Preparing your guide… |
| `chat.status.reading_photo` | Reading your photo… |
| `chat.sent` | Sent |
| `a11y.back` | Back |
| `a11y.menu` | Menu |
| `a11y.new_chat` | New guide |
| `a11y.close` | Close |
| `a11y.share` | Share guide |
| `a11y.wardrobe_button` | Capsule, AI stylist. Wardrobe: {wardrobe}. Change wardrobe |
| `a11y.camera` | Add a photo of your clothes |
| `a11y.mic` | Record a voice message |
| `a11y.mic_stop` | Stop recording |
| `a11y.send` | Send |
| `a11y.stop` | Stop writing the guide |
| `a11y.msg_capsule` | Capsule said: {text} |
| `a11y.msg_user` | You said: {text} |
| `a11y.msg_voice` | Your voice message, {duration}. Transcript: {transcript} |
| `a11y.msg_photo` | Your photo. Clothes found: {items} |
| `a11y.recording` | Recording |
| `a11y.recording_elapsed` | {seconds} seconds |
| `a11y.guide_ready` | Guide ready |
| `a11y.style_count` | {n} of 3 selected |
| `a11y.style_max` | Unavailable, maximum 3 |
| `a11y.size_picker` | {category} size, {system}, {value} |
| `a11y.item_link` | View at {shop}, opens in your browser |
| `a11y.budget_summary` | {total} of {budget} spent, within budget, {left} left |
| `a11y.budget_summary_over` | {total} of {budget}, over budget by {over}. Prices have changed since this guide was made |
| `a11y.helpful_yes` | This guide was helpful |
| `a11y.helpful_no` | This guide was not helpful |
| `a11y.more_guide` | More options for {guide_title} |

## Onboarding

| Id | Text |
| --- | --- |
| `onb.welcome.title` | Your stylist for any occasion |
| `onb.welcome.body` | Tell me where you're going and what you want to spend. I'll reuse clothes you already own, tell you what matters most and why, and the total always stays within your budget. |
| `onb.welcome.cta` | Get started |
| `onb.welcome.legal` | By continuing, you agree to the Terms. The Privacy notice explains how we handle your data. |
| `onb.consent.title` | Help us improve Capsule? |
| `onb.consent.body` | You choose what the app may send us. Both are off until you turn them on, and you can change this at any time. |
| `onb.consent.crash.label` | Crash reports |
| `onb.consent.crash.desc` | Technical details when the app crashes or runs slowly, so we can fix it. No messages, photos or screenshots. |
| `onb.consent.usage.label` | Usage events |
| `onb.consent.usage.desc` | Which steps you complete, such as "guide finished", so we can see what works. Linked to a random id, not your name or email. |
| `onb.consent.details_toggle` | What we collect |
| `onb.consent.details` | We collect: when you open the app, which steps you complete, the wardrobe you pick (menswear, womenswear or unisex), how long a guide takes, whether it stayed within budget, whether you used text, voice or a photo, whether you rated a guide helpful, whether you created an account, and technical details of crashes. We never collect: your messages, photos, voice notes, sizes, budget, details of your occasion or screenshots. Sentry (crash reports) and PostHog (usage events) store this in the EU and process it only for us. More in the Privacy notice. |
| `onb.consent.change_later` | You can change this any time in Settings › Privacy. |
| `onb.consent.allow` | Allow both |
| `onb.consent.decline` | Don't allow |
| `onb.consent.save` | Save my choice |
| `onb.progress` | Step {n} of 3 |
| `onb.continue` | Continue |
| `onb.skip` | Skip for now |
| `onb.wardrobe.title` | Which wardrobe should I shop for? |
| `onb.wardrobe.helper` | This only sets which shop sections I search. You can change it at any time, even for a single guide. |
| `onb.wardrobe.men` | Menswear |
| `onb.wardrobe.men.desc` | Clothes from menswear sections |
| `onb.wardrobe.women` | Womenswear |
| `onb.wardrobe.women.desc` | Clothes from womenswear sections |
| `onb.wardrobe.unisex` | Unisex |
| `onb.wardrobe.unisex.desc` | Clothes from both, or unisex lines |
| `onb.style.title` | Which styles feel like you? |
| `onb.style.helper` | Pick up to three, or none. I'll use them as a starting point, not a rule. |
| `onb.style.options` | Classic · Relaxed · Minimal · Smart casual · Sporty · Colourful · Outdoor · Vintage |
| `onb.style.max` | You can pick up to three. |
| `onb.sizes.title` | The sizes you usually buy |
| `onb.sizes.helper` | So I only suggest things you can order in your size. Skip any you're not sure about. |
| `onb.sizes.system` | Size system |
| `onb.sizes.tops` | Tops |
| `onb.sizes.bottoms` | Bottoms |
| `onb.sizes.shoes` | Shoes |
| `onb.sizes.not_set` | Not set |
| `onb.sizes.privacy` | Sizes are used only to filter products. They are never sent in usage events. |

## Chat

| Id | Text |
| --- | --- |
| `chat.empty.greeting` | Hi! Tell me where you're headed and what you want to spend, and I'll put together a look that fits your budget. You can type, send a voice message or add a photo of clothes you already own. |
| `chat.empty.examples_label` | For example: |
| `chat.empty.example_1` | Job interview at a design studio, €100 |
| `chat.empty.example_2` | Outdoor summer wedding, I'm a guest, €150 |
| `chat.empty.example_3` | First date, dinner then a walk, €60 |
| `chat.followup.intro` | A couple of quick questions so the look suits the occasion: |
| `chat.followup.wardrobe` | Which wardrobe should I shop for? I'll remember it for next time. |
| `chat.followup.voice_hint` | You can also reply by voice or send a photo of what you already own. |
| `chat.composer.placeholder` | Message Capsule… |
| `chat.composer.placeholder_busy` | You can type while I work… |
| `chat.composer.placeholder_offline` | Type now, it'll send when you're back online |
| `chat.stop` | Stop |
| `chat.stopped` | Stopped. Nothing was saved. |

## Guide progress (C2)

| Id | Text |
| --- | --- |
| `guide.progress.understood` | Understood your request: {summary} |
| `guide.progress.photo` | Analysed your photo: {items} |
| `guide.progress.found` | Found {n} new pieces |
| `guide.progress.found_one` | Found 1 new piece |
| `guide.progress.budget` | Checked budget: {total} of {budget} |
| `guide.progress.writing` | Writing your guide |

## Photo and voice

| Id | Text |
| --- | --- |
| `photo.source.camera` | Take a photo |
| `photo.source.library` | Choose from library |
| `photo.preview.send` | Send |
| `photo.preview.retake` | Retake |
| `photo.item.in_look` | in the look |
| `photo.item.not_used` | not used |
| `photo.privacy_note` | I only look at the clothes. Capsule doesn't keep your photo on this phone, and our server deletes it once it's processed, always within 24 hours. |
| `voice.recording` | Recording… |
| `voice.cancel` | Cancel |
| `voice.limit` | Voice messages can be up to 1 minute. |
| `voice.too_short` | That was too short to hear. Tap the microphone, speak, then tap again to stop. |
| `voice.transcribing` | Writing down what you said… |
| `voice.transcript_label` | Transcript |
| `voice.edit` | Edit |

## Permissions

| Id | Text |
| --- | --- |
| `perm.camera.title` | Take a photo of your clothes |
| `perm.camera.body` | I'll use it to see which clothes you already own so I can build the look around them. I only look at the clothes, and the photo is deleted within 24 hours. |
| `perm.camera.denied` | Camera access is off. To take a photo, turn it on in Settings. You can still type or choose a photo from your library. |
| `perm.photos.title` | Choose a photo of your clothes |
| `perm.photos.body` | I'll only see the photo you pick, not the rest of your library. I only look at the clothes, and our copy is deleted within 24 hours. |
| `perm.photos.denied` | Photo access is off. To choose a photo, turn it on in Settings. You can still type or use the camera. |
| `perm.mic.title` | Talk instead of typing |
| `perm.mic.body` | I'll turn your voice message into text so you can check it before I answer. I only use your words, not how you sound. The recording isn't kept on this phone, and our server deletes it once it's transcribed, always within 24 hours. |
| `perm.mic.denied` | Microphone access is off. To send voice messages, turn it on in Settings. You can still type. |
| `perm.continue` | Continue |
| `perm.not_now` | Not now |
| `perm.open_settings` | Open Settings |

## Guide

| Id | Text |
| --- | --- |
| `guide.title` | Your guide |
| `guide.wardrobe_label` | {wardrobe} |
| `guide.wardrobe_change` | Change |
| `guide.budget.label` | Budget |
| `guide.budget.amount` | {total} of {budget} |
| `guide.budget.checked` | Within budget · {left} left |
| `guide.budget.over` | Over budget by {over} · prices have changed |
| `guide.section.key` | The key pieces |
| `guide.section.key.sub` | They carry the whole look. Buy these first. |
| `guide.section.base` | The base |
| `guide.section.base.sub` | Neutral pieces that tie the key ones together. |
| `guide.section.details` | The details |
| `guide.section.details.sub` | Finish the look if the budget allows. |
| `guide.item.view` | View at {shop} |
| `guide.item.owned` | From your photo |
| `guide.item.unavailable` | No longer available at this price. |
| `guide.item.find_alternative` | Find an alternative |
| `guide.why.title` | Why this works |
| `guide.feedback.question` | Was this guide helpful? |
| `guide.feedback.thanks` | Thanks, that helps me get better. |
| `guide.feedback.reason_title` | What didn't work? (optional) |
| `guide.feedback.reasons` | Too expensive · Not my style · Wrong for the occasion · Something else |
| `guide.save` | Save guide |
| `guide.saved` | Saved |
| `guide.on_device` | Saved on this phone |

## Guest → sign-up

| Id | Text |
| --- | --- |
| `save.sheet.title` | Keep this guide? |
| `save.sheet.body` | Create a free account to keep your guides on any phone, and safe if you delete the app. Your chats and choices so far come with you. |
| `save.sheet.create` | Create account |
| `save.sheet.local` | Save on this phone |
| `save.sheet.local_warning` | A guide saved on this phone is lost if you delete the app or change phone. Without an account, we delete your guest data from our server after {retention_days} days without use. |
| `save.sheet.offline` | You need a connection to create an account. You can save the guide on this phone for now. |
| `save.done_account` | Saved to your account. |
| `save.done_local` | Saved on this phone. |
| `save.inline_link` | Keep your guides on any phone: create an account |
| `saved.return_banner.title` | Your saved guides are only on this phone |
| `saved.return_banner.body` | Create a free account so you don't lose them if you delete the app or change phone. |
| `saved.return_banner.create` | Create account |
| `saved.return_banner.dismiss` | Not now |

## Saved guides

| Id | Text |
| --- | --- |
| `saved.title` | Saved guides |
| `saved.row.summary` | {count} pieces · {total} of {budget} |
| `saved.empty.title` | No saved guides yet |
| `saved.empty.body` | When a guide is ready, tap "Save guide" and it will appear here, even without a connection. |
| `saved.empty.cta` | Start a guide |
| `saved.delete.action` | Delete guide |
| `saved.delete.title` | Delete this guide? |
| `saved.delete.body` | It will be deleted from this phone. This can't be undone. |
| `saved.delete.body_account` | It will be deleted from your account and every phone you use. This can't be undone. |
| `saved.delete.confirm` | Delete |
| `saved.delete.cancel` | Keep it |

## Change wardrobe

| Id | Text |
| --- | --- |
| `wardrobe.change.title_guide` | Wardrobe for a new guide |
| `wardrobe.change.title_profile` | Your wardrobe |
| `wardrobe.change.helper` | I'll make a new guide for the same occasion and budget. This one stays as it is. |
| `wardrobe.change.helper_profile` | Used for your next guides. You can change it at any time. |
| `wardrobe.change.current` | Current |
| `wardrobe.change.make_default` | Use this wardrobe from now on |
| `wardrobe.change.cta_guide` | Make a new guide |
| `wardrobe.change.cta_profile` | Save |
| `wardrobe.change.cancel` | Cancel |

## Privacy settings

| Id | Text |
| --- | --- |
| `privacy.export` | Download my data |
| `privacy.delete` | Delete my data |
| `privacy.delete.title` | Delete all your data? |
| `privacy.delete.body_guest` | This deletes your guides, chats and choices from this phone and from our server, along with any crash reports and usage events linked to you. This can't be undone. |
| `privacy.delete.body_account` | This deletes your account, guides, chats and choices from every phone and from our server, along with any crash reports and usage events linked to you. This can't be undone. |
| `privacy.delete.confirm` | Delete everything |

## Offline

| Id | Text |
| --- | --- |
| `offline.banner` | You're offline. Saved guides still work, and new messages will send once you're back online. |
| `offline.welcome` | You'll need a connection to get your first guide. |
| `offline.back_online` | You're back online. |
| `offline.queued` | Waiting for connection · sends automatically |
| `offline.queued_old` | Not sent yet. Send it now or delete it? |
| `offline.queued_send` | Send now |
| `offline.queued_delete` | Delete |
| `offline.media_disabled` | Photos and voice messages need a connection. |
| `offline.link_disabled` | Shop links open when you're back online. |
| `offline.refresh_disabled` | You're offline. Showing guides saved on this phone. |

## Errors

Pattern: what happened, in plain words → what the user can do. No codes, no blame.

| Id | Text |
| --- | --- |
| `error.server.title` | I can't connect right now |
| `error.server.body` | This is on our side. Please try again in a moment. |
| `error.try_again` | Try again |
| `error.connection_dropped` | I couldn't answer "{message_excerpt}": the connection dropped. |
| `error.guide.timeout` | This is taking longer than it should. Try again, or simplify the request. |
| `error.guide.no_fit` | I couldn't build a full look within {budget}. Here's what we can do: |
| `error.guide.no_fit.own` | Use more of my own clothes |
| `error.guide.no_fit.key_only` | Show the key piece only |
| `error.guide.no_fit.budget` | Change budget |
| `error.guide.load` | This guide didn't load. |
| `error.photo.invalid` | I can't use this file. Send a JPEG, PNG or HEIC photo. |
| `error.photo.upload` | The photo didn't upload. |
| `error.photo.no_clothes` | I couldn't find any clothes in this photo. Try one with the clothes laid flat or on a hanger, in good light. |
| `error.photo.analysis` | I couldn't read this photo. Try again, or describe the clothes in a message. |
| `error.voice.transcribe` | I couldn't make out that voice message. |
| `error.voice.type_instead` | Type instead |
| `error.saved.refresh` | Couldn't refresh your guides. Showing the ones on this phone. |
