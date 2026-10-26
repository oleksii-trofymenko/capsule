# Metrics

Every task card names one metric from this file: a product metric or an engineering SLO. Harness and docs-only cards may write `n/a — <reason>` instead. A new metric is added here, with how it is measured, before a card can use it.

## Product

| Metric | Meaning | MVP target | How we measure |
| --- | --- | --- | --- |
| Activation rate | New users who receive their first guide | > 60% | `guide_delivered` / `signup` |
| Time to first guide | App open to first guide | p95 < 90 s | Analytics events |
| Guide quality score | Eval score (LLM-as-judge + rules) | > 4.0 / 5 | Eval suite in CI |
| Budget compliance | Guides whose total ≤ budget | 100% | Code validator + eval |
| Helpful rate | Guides rated helpful | > 70% | 👍 / 👎 in the guide |
| D7 retention | Users back after 7 days | > 20% | Cohort analytics |
| Click-through | Product link opened from a guide | > 15% | `product_click` |

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
