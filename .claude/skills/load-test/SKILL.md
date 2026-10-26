---
name: load-test
description: Write and run a k6 load scenario and report where latency breaks and what saturates first. Use before releases and when a card touches latency or capacity.
---

# Load test

1. **Scenario.** A k6 script in `infra/k6/` that follows a real user path (sign in → ask → follow-up → guide), with think time.
2. **Targets.** Thresholds from `docs/metrics.md`: p95/p99 per endpoint, error rate.
3. **Steps.** Run at 10, 25 and 50 virtual users, a few minutes each, against the home server (never against shared or third-party services).
4. **Watch.** Grafana during the run: GPU and VRAM, queue depth, CPU, DB connections, Redis.
5. **Find the knee.** The load where p95 crosses the target, and the resource that saturated first.
6. **Report** in `docs/reports/load-<date>.md`: a table per step (VUs, p50, p95, p99, errors), the bottleneck, and one recommended next step.
