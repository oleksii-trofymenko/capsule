---
name: agent-node
description: Add or change a node in the LangGraph agent with typed input/output, timeout, fallback, tracing and fixture tests. Use for any change to the agent graph.
---

# Agent node

1. **Contract.** Define the node's input and output as Pydantic models. A node reads only the state fields it needs and writes only its own.
2. **Single job.** One node, one responsibility (parse request, ask follow-ups, retrieve trends, search products, validate budget, write guide, check output).
3. **Model calls.** Through the LiteLLM gateway only, with the `openai` client and a logical route name from gateway config (`agent-parse`, `agent-guide`, `vision`, `embed`; ADR-010). Never a model name, provider or LangChain chat-model wrapper in code (ADR-009). Send the node name as request metadata. Structured output via schema; invalid → one retry → the route's configured fallback, which is another local route: no cloud route exists while the budget is €0 (ADR-010). If that fails too, the node returns a typed failure and the graph answers "try again later"; it never crashes.
4. **Deterministic checks are code.** Budget sums, currency, product existence and links are checked in Python, not by a model.
5. **Limits.** A timeout per node and a total for the graph. Loops (clarify, re-pick within budget) have a max count.
6. **State.** Checkpointed in Postgres (`langgraph-checkpoint-postgres`, separate `agent_checkpoint` schema created by an Alembic migration, never by `setup()` at runtime; ADR-009) so a conversation resumes after a follow-up question. Checkpoints are deleted when the consultation closes or expires, because state holds personal data.
7. **Tracing.** A Langfuse span with node name, model, tokens, latency; no raw photos, no personal data.
8. **Tests.** Unit test on recorded fixtures (no live model) for the happy path, invalid model output and timeout.
9. **Eval.** If the node changes answers, run the `eval-run` skill and put the delta in the PR.
