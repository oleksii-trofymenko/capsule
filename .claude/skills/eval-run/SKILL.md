---
name: eval-run
description: Run the eval suite and produce a comparable report with deltas against the baseline. Use after any change to prompts, models, quantisation or agent nodes, and in QA.
---

# Eval run

1. **Pin the setup.** Record prompt versions, model aliases and the models they resolve to, quantisation, gateway config, git SHA.
2. **Run.** `make eval` (or the runner in `ml/evals/` with a filter for a quick subset while iterating; the full suite for the PR).
3. **Metrics.** Mean quality score (LLM-as-judge, 1–5), budget compliance, structure validity, hallucinated products, p50/p95 latency, tokens per guide.
4. **Slices.** Show the score by wardrobe (menswear, womenswear, unisex), by event and by budget band. A drop in one slice is a regression even if the mean rises.
5. **Worst cases.** List the 5 lowest-scored answers with the judge's reason.
6. **Compare.** Delta against the baseline report in `ml/evals/reports/baseline.json`.
7. **Save.** Write the report to `ml/evals/reports/<date>-<sha>.md`. Update the baseline only when the Orchestrator accepts the change.
8. **Return** a short table and the report path, not the raw output.
