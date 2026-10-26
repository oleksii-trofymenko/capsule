---
name: release
description: Cut a mobile and backend release with versioning, changelog, staged rollout and feature flags. Use when an epic is ready to ship to testers or the stores.
---

# Release

1. **Gate.** All epic cards accepted; CI green; eval and load reports attached; no open critical or high security findings.
2. **Version.** Semantic version for the API and the app; bump the minimum supported app version only if the API breaks old clients.
3. **Changelog.** User-facing changes in plain English; internal notes separately.
4. **Backend.** Tag, build images, run migrations, deploy, check `/ready` and the dashboards for 15 minutes.
5. **Mobile.** EAS Build for both platforms. Native changes → store build; JS-only changes → EAS Update to the matching runtime version.
6. **Flags.** New features behind a PostHog flag, off by default.
7. **Rollout.** 10% → 50% → 100%, moving on only if crash-free sessions > 99.5% and error rate within target.
8. **Rollback.** Know the command before you start: previous image tag, previous EAS Update, flag off.
9. **Report.** What shipped, rollout numbers, issues seen.
