---
name: agent-node
description: Add or change a node in the LangGraph agent with typed input/output, timeout, fallback, tracing and fixture tests. Use for any change to the agent graph.
---

# Agent node

1. **Contract.** Define the node's input and output as Pydantic models. A node reads only the state fields it needs and writes only its own.
2. **Single job.** One node, one responsibility (parse request, ask follow-ups, retrieve trends, search products, validate budget, write guide, check output).
3. **Model calls.** Through the gateway only, with a model alias from config (e.g. `fast`, `guide`, `vision`). Structured output via schema; invalid → one retry → fallback alias.
4. **Deterministic checks are code.** Budget sums, currency, product existence and links are checked in Python, not by a model.
5. **Limits.** A timeout per node and a total for the graph. Loops (clarify, re-pick within budget) have a max count.
6. **State.** Checkpointed in Postgres so a conversation resumes after a follow-up question.
7. **Tracing.** A Langfuse span with node name, model, tokens, latency; no raw photos, no personal data.
8. **Tests.** Unit test on recorded fixtures (no live model) for the happy path, invalid model output and timeout.
9. **Eval.** If the node changes answers, run the `eval-run` skill and put the delta in the PR.
