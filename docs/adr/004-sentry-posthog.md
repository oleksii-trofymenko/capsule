# ADR-004: Sentry for crashes and performance, PostHog for analytics and feature flags

- Status: proposed
- Date: 2026-10-26
- Deciders: Orchestrator, mobile-engineer, security-engineer, project owner
- Related: E0-03, ADR-001, ADR-013 (planned), blueprint §1, §10, §11

## Context

The success metrics (blueprint §1) need product events: activation, time to first guide, helpful rate, D7 retention, click-through. Quality targets (blueprint §10) need crash-free rate > 99.5 %, app start and slow-frame data per release. Releases need feature flags and staged rollout 10 % → 50 % → 100 %. Users are in Europe, so data must stay in the EU and analytics must respect consent.

## Options

1. **Sentry (crashes, performance, release health) + PostHog (events, funnels, cohorts, flags), both on EU hosting** — each is best at its job; both have Expo SDKs and free tiers that fit an MVP; PostHog can be self-hosted later. Cons: two vendors, two SDKs in the bundle.
2. **Firebase (Crashlytics + Analytics + Remote Config)** — one SDK, free. Lost: weaker funnels and cohort analysis, data processed by Google outside our control, and Expo integration needs native config.
3. **Self-hosted only (GlitchTip + Umami or our own events table)** — full data control. Lost: more infrastructure on the home server and no mature mobile release-health or flag tooling.

## Decision

Use Sentry for crashes, performance and release health, and PostHog for product analytics and feature flags, both on EU data regions, with analytics only after user consent and no personal data or photos in events.

## Consequences

- Easier: metrics from blueprint §1 and §10 come from dashboards on day one; staged rollout via flags.
- Harder: an event schema to maintain (cards list their analytics events); consent handling in onboarding.
- We will monitor: free-tier quotas, SDK impact on cold start and bundle size.
- Revisit when: monthly cost exceeds the free tiers by a clear margin, or EU data-residency rules require self-hosting.
