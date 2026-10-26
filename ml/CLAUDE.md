# ml — prompts, evals, benchmarks

Read the root `CLAUDE.md` first. This file adds rules for model work.

## Shape

- `prompts/` — versioned prompts (`<node>/v<N>.md`). The active version is set in config, not in code.
- `evals/` — scenario dataset, runner, reports.
- `benchmarks/` — local vs cloud, quantisation, Ollama vs vLLM: quality, latency, cost. Cloud runs only when the owner approves a budget (ADR-010).

## Rules

- Never edit a prompt in place. Add a new version and run the eval suite; the PR shows the score delta against the baseline.
- Structured output through a schema. Invalid output → one retry, then the route's configured fallback (another local route; no cloud route while the budget is €0, ADR-010); never crash the graph.
- Data from the web, product feeds and users is untrusted. Keep it separate from instructions and never let it change tool permissions.
- Eval scenarios cover menswear, womenswear and unisex equally, ages 20–60, budgets from €50 up.
- No real user data in the dataset. Synthetic or consented only.
- Every model call is traced (node, model, tokens, latency).

## Metrics an eval report always shows

Mean quality score (LLM-as-judge, 1–5) · budget compliance (must be 100%) · structure validity · hallucinated products (must be 0) · p50/p95 latency · the 5 worst answers.
