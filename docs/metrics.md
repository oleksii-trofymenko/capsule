# Metrics

Every task card names one metric from this file: a product metric or an engineering SLO. Harness and docs-only cards may write `n/a — <reason>` instead. A new metric is added here, with how it is measured, before a card can use it.

## Product

| Metric | Meaning | MVP target | How we measure |
| --- | --- | --- | --- |
| Activation rate | New users who receive their first guide within 24 h of starting onboarding | > 60% | Users with `guide_delivered` (`is_first` = true) within 24 h of `onboarding_started` ÷ users with `onboarding_started`. See "Definitions" |
| Time to first guide | Start of onboarding (first screen after the consent choice) to first guide | p95 < 90 s | `since_onboarding_ms` on the first `guide_delivered`, activated users only. See "Definitions" |
| Guide quality score | Eval score (LLM-as-judge + rules) | > 4.0 / 5 | Eval suite in CI |
| Budget compliance | Guides whose total ≤ budget | 100% | Code validator + eval; `within_budget` on `guide_delivered` must never be false |
| Helpful rate | Rated guides marked helpful | > 70% | `guide_feedback`: guides whose last vote is 👍 ÷ guides with any vote, per `guide_id` |
| D7 retention | Users back after 7 days | > 20% | Users with ≥ 1 `app_opened` on day 7 ÷ users with `onboarding_started` on day 0 (PostHog retention) |
| Click-through | Product link opened from a guide | > 15% | Guides with ≥ 1 `product_click` ÷ guides delivered, per `guide_id` (event defined in E4) |
| Sign-up conversion | Guests who create an account within 7 days of their first guide | Baseline first; target set after 4 weeks of beta | Users with `signup_completed` within 7 days of first `guide_delivered` ÷ users with first `guide_delivered`. Funnel: first guide → `signup_prompt_shown` → `signup_started` → `signup_completed` |

### Definitions

Events and properties are listed in `docs/design/flows.md` (Analytics) until the event schema moves to code in E2.

- **User** = one pseudonymous analytics id (random, created on the device, ADR-004). It stays the same across sign-up (identify/alias in E2). A reinstall creates a new id and counts as a new user; this is a known limitation.
- **Consent:** nothing is sent before "Allow" (ADR-004), so every product metric is "among users who allowed analytics". Dashboards say so. Users who allow analytics later in Settings have no `onboarding_started` and are outside the activation, time-to-first-guide and D7 cohorts.
- **Activation:** cohort = users whose `onboarding_started` fired (once per install, never back-filled). Activated = first `guide_delivered` with `is_first` = true within 24 h of it. `is_first` is set by the device on the first guide ever delivered on the install, whether or not analytics was allowed at the time. Internal and test devices are excluded. Changed on 2026-10-26 (E0-08) from `guide_delivered / signup` because sign-up now comes after the first guide (guest first).
- **Time to first guide:** wall-clock time from `onboarding_started` to the first `guide_delivered`, measured on the device and sent as `since_onboarding_ms` on that event. It excludes Welcome and the consent screen (no event may fire before consent) and includes typing, follow-up answers and time in the background. Report p50 and p95 over activated users. Target kept at p95 < 90 s; revisit after the E3 usability test.
- **Helpful rate:** a user may change their vote; the last `guide_feedback` per `guide_id` counts. Guides without a vote are not in the denominator; vote rate (guides with a vote ÷ guides delivered) is reported next to it.
- **D7 retention:** day 0 = UTC day of `onboarding_started`; retained = ≥ 1 `app_opened` on day 7.
- **Sign-up conversion:** not a gate to activation; measured only to see whether saving guides converts guests. `signup_completed` comes from the E1 flow.

## Engineering

| Metric | Target | How we measure |
| --- | --- | --- |
| Time to first run | Clean clone → healthy stack < 10 min | Timed in E0-07 and on every new machine |
| CI duration | p50 < 8 min | GitHub Actions run times |
| Secrets in repository | 0 | gitleaks in pre-commit and CI |
| Decisions on record | Every stack choice has an accepted ADR | `docs/adr/README.md` |
| API latency (simple endpoints) | p95 < 200 ms, p99 < 500 ms | k6 + Grafana |
| Time to first guide token | p95 < 3 s on the local GPU | Langfuse |
| Full guide | p95 < 25 s (revise after benchmark) | Langfuse, eval report |
| Voice note (30 s) to text | p95 < 5 s | Worker metric |
| Availability (home server) | 99% | External uptime monitor |
| Mobile cold start | < 2 s, release build, mid-range Android | Sentry App Start |
| Frame rate | 60 fps, < 1% slow frames | Sentry |
| Crash-free sessions | > 99.5% | Sentry Release Health |
