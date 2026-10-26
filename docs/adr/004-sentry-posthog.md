# ADR-004: Sentry for crashes and performance, PostHog for analytics and feature flags

- Status: accepted (2026-10-26)
- Date: 2026-10-26
- Deciders: Orchestrator, mobile-engineer, security-engineer, project owner
- Related: E0-03, ADR-001, ADR-013 (planned), blueprint §1, §10, §11

## Context

The success metrics (blueprint §1) need product events: activation, time to first guide, helpful rate, D7 retention, click-through. Quality targets (blueprint §10) need crash-free rate > 99.5 %, app start and slow-frame data per release, plus feature flags. The project runs at zero cost: no paid plans, no card on file. Users are in Europe, so data must stay in the EU, analytics must wait for consent, and screens show users' outfit photos, so nothing may record the screen.

## Options

1. **Sentry (crashes, performance, release health) + PostHog (events, funnels, cohorts, flags), both on EU hosting** — each is best at its job; both have Expo SDKs and free tiers that fit an MVP; PostHog can be self-hosted later. Cons: two vendors, two SDKs in the bundle.
2. **Firebase (Crashlytics + Analytics + Remote Config)** — one SDK, free. Lost: weaker funnels and cohort analysis, data processed by Google outside our control, and Expo integration needs native config.
3. **Self-hosted only (GlitchTip + Umami or our own events table)** — full data control. Lost: more infrastructure on the home server and no mature mobile release-health or flag tooling.

## Decision

Use Sentry (`@sentry/react-native` with its Expo plugin) for crashes, performance and release health, and PostHog for product analytics and feature flags, both in EU data regions on their free plans only (no payment method on either account, so usage can never be billed), configured privacy-first: Sentry with `sendDefaultPii: false`, no screenshots, attachments or session replay, and a `beforeBreadcrumb`/`beforeSend` that strips auth headers, tokens and request bodies; PostHog with autocapture and session replay off, only events from the card-defined schema, nothing captured before consent (flags fall back to coded defaults), and users identified only by a random pseudonymous id.

## Consequences

- Easier: metrics from blueprint §1 and §10 come from dashboards on day one; feature gating via PostHog flags. Staged rollout itself uses Play staged rollout, App Store phased release and `eas update --rollout-percentage`; forced update uses the API minimum version (blueprint §10).
- Harder: an event schema to maintain (cards list their analytics events); consent handling in onboarding; nothing critical may depend on a flag; source maps uploaded for every EAS build and update; a signed DPA with each vendor, and account deletion also deletes the person in PostHog and their data in Sentry.
- We will monitor: free-plan quotas (events dropped at the limit are acceptable), SDK impact on cold start and bundle size.
- Revisit when: either vendor would require a paid plan or a payment method (the project budget is €0), the SDKs add > 150 ms to cold start or > 3 MB installed size, or EU data-residency rules require self-hosting.
